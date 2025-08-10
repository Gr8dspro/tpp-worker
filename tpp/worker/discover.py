import asyncio, os, math, json, re
from slugify import slugify
from bs4 import BeautifulSoup

from .config import CFG, TPP_ENDPOINT, TPP_SECRET
from .merchants.common import Fetcher, parse_sitemap
from .util.jsonld import extract_product_ld
from rapidfuzz import fuzz

def looks_discontinued_or_oos(name:str, html:str, ld:dict)->str:
    name = (name or "").lower()
    html_l = (html or "").lower()
    if any(k in name for k in ["discontinued","legacy","out of stock","oos","clearance"]):
        return "discontinued"
    avail = (ld or {}).get("availability") or ""
    if isinstance(avail, str) and avail.lower() != "instock":
        return "oos"
    if "out of stock" in html_l or "no longer available" in html_l:
        return "oos"
    return ""

def pick_reason(base, alt):
    reasons = []
    bp = base.get("price"); ap = alt.get("price")
    try:
        bpv = float(re.sub(r"[^0-9.]", "", str(bp))) if bp else None
        apv = float(re.sub(r"[^0-9.]", "", str(ap))) if ap else None
    except Exception:
        bpv = apv = None
    if bpv and apv:
        delta = (bpv - apv) / bpv
        if delta > 0.15:
            reasons.append(f"~{int(delta*100)}% cheaper than {base.get('name','X')}")
    if alt.get("rating") and base.get("rating"):
        try:
            if float(alt["rating"]) - float(base["rating"]) >= 0.2:
                reasons.append("Higher user rating")
        except Exception:
            pass
    if (alt.get("availability") or "").lower() == "instock":
        reasons.append("In stock")
    return "; ".join(reasons) or "Comparable spec and value"

async def gather_candidates(fetcher:Fetcher, urls:list, max_pages:int=500):
    products = []
    for url in urls[:max_pages]:
        html, etag, last = await fetcher.get(url)
        if not html: 
            continue
        ld = extract_product_ld(html)
        name = ld.get("name")
        if not name:
            # try title
            soup = BeautifulSoup(html, "lxml")
            t = soup.title.string if soup.title else None
            name = t.strip() if t else None
        products.append({"url":url, **ld, "name":name})
    return products

async def main():
    assert TPP_ENDPOINT and TPP_SECRET, "Set TPP_ENDPOINT and TPP_SECRET env vars"
    fetcher = Fetcher()
    try:
        # 1) Load product URLs from sitemaps
        urls = []
        for sm in CFG.get("sitemaps", []):
            xml, _, _ = await fetcher.get(sm)
            if not xml: 
                continue
            urls.extend(await parse_sitemap(xml))
        urls = list(dict.fromkeys(urls))  # dedupe
        # 2) Pull a small sample from head to keep polite (adjust higher later)
        urls = urls[:300]

        # 3) Fetch base products
        base_products = await gather_candidates(fetcher, urls, max_pages=200)
        # Filter to discontinued/OOS
        discontinueds = []
        for p in base_products:
            html, _, _ = await fetcher.get(p["url"])
            if not html:
                continue
            status = looks_discontinued_or_oos(p.get("name"), html, p)
            if status:
                p["status"] = status
                discontinueds.append(p)

        # 4) Build a candidate alt pool (reuse same urls for demo)
        alt_pool = [a for a in base_products if (a.get("availability") or "").lower() == "instock"]
        # 5) For each discontinued, pick top 3–6 alts by fuzzy name match
        items = []
        for base in discontinueds[:50]:
            scores = []
            for alt in alt_pool:
                if alt["url"] == base["url"]:
                    continue
                s = fuzz.token_set_ratio(base.get("name") or "", alt.get("name") or "")
                scores.append((s, alt))
            scores.sort(reverse=True, key=lambda x: x[0])
            picks = []
            for s, alt in scores[:8]:
                reason = pick_reason(base, alt)
                picks.append({
                    "name": alt.get("name") or "Alternative",
                    "url": alt["url"],
                    "price": f"${alt['price']}" if alt.get("price") and not str(alt["price"]).startswith("$") else alt.get("price"),
                    "merchant": "",
                    "reason": reason
                })
            picks = picks[:6]
            if picks:
                items.append({
                    "original_name": base.get("name") or "Original Product",
                    "original_url": base["url"],
                    "status": base.get("status","discontinued"),
                    "slug": slugify((base.get("name") or "original")[:80]),
                    "explanation": "Selected by similarity, price/availability, and ratings where available.",
                    "alternatives": picks
                })

        # 6) POST in chunks
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            CHUNK = 25
            for i in range(0, len(items), CHUNK):
                batch = {"items": items[i:i+CHUNK]}
                r = await client.post(TPP_ENDPOINT, headers={
                    "Content-Type":"application/json",
                    "X-TPP-Secret":TPP_SECRET
                }, json=batch)
                print("POST", i, r.status_code, r.text[:200])

    finally:
        await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
