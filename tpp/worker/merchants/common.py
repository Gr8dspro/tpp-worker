import httpx, asyncio, time, re
from urllib.parse import urlparse
from lxml import etree
from .robots import Robots

from ..config import USER_AGENT, MAX_PER_HOST_RPS

class Fetcher:
    def __init__(self):
        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        self.client = httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT}, limits=limits)
        self.robots_cache = {}
        self.last = {}

    async def close(self):
        await self.client.aclose()

    async def allowed(self, url:str)->bool:
        host = urlparse(url).netloc
        if host not in self.robots_cache:
            try:
                r = await self.client.get(f"https://{host}/robots.txt")
                txt = r.text if r.status_code == 200 else ""
            except Exception:
                txt = ""
            self.robots_cache[host] = Robots(txt)
        return self.robots_cache[host].allowed(url, "*")

    async def throttle(self, url:str):
        host = urlparse(url).netloc
        now = time.time()
        last = self.last.get(host, 0.0)
        min_gap = 1.0 / MAX_PER_HOST_RPS
        if now - last < min_gap:
            await asyncio.sleep(min_gap - (now - last))
        self.last[host] = time.time()

    async def get(self, url:str, etag:str=None, last_mod:str=None):
        if not await self.allowed(url):
            return None, None, None
        await self.throttle(url)
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_mod:
            headers["If-Modified-Since"] = last_mod
        r = await self.client.get(url, headers=headers, follow_redirects=True)
        if r.status_code == 304:
            return None, etag, last_mod
        new_etag = r.headers.get("ETag")
        new_last = r.headers.get("Last-Modified")
        return r.text, new_etag, new_last

async def parse_sitemap(xml_text:str):
    urls = []
    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
    except Exception:
        return urls
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc in root.xpath("//sm:url/sm:loc/text()", namespaces=ns):
        urls.append(loc.strip())
    return urls
