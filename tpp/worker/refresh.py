import asyncio, os, json, re
from rapidfuzz import fuzz
from slugify import slugify
from bs4 import BeautifulSoup

from .config import CFG, TPP_ENDPOINT, TPP_SECRET
from .merchants.common import Fetcher, parse_sitemap
from .util.jsonld import extract_product_ld

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
            reasons.append(f"~{int(delta*100)}% cheaper")
    if (alt.get("availability") or "").lower() == "instock":
        reasons.append("In stock")
    if alt.get("rating"):
        reasons.append(f"Rated {alt['rating']}")
    return "; ".join(reasons) or "Comparable spec and value"

async def main():
    assert TPP_ENDPOINT and TPP_SECRET, "Set TPP_ENDPOINT and TPP_SECRET env vars"
    fetcher = Fetcher()
    try:
        # Use sitemaps as a light proxy for "what to refresh" in this starter.
        urls = []
        for sm in CFG.get("sitemaps", []):
            xml, _, _ = await fetcher.get(sm)
            if not xml:
                continue
            urls.extend(await parse_sitemap(xml))
        urls = list(dict.fromkeys(urls))[:250]

        # Fetch and compose quick pairs (base vs alt from the same pool)
        products = []
        for url in urls:
            html,_,_ = await fetcher.get(url)
            if not html: 
                continue
            ld = extract_product_ld(html)
            name = ld.get("name")
            if not name:
                soup = BeautifulSoup(html, "lxml")
                name = soup.title.string.strip() if soup.title else None
            products.append({"url":url, **ld, "name":name})

        # naive refresh: pick a subset and post updates to ensure lastmod bumps on meaningful changes
        items = []
        instock = [p for p in products if (p.get("availability") or "").lower() == "instock"]
        oos = [p for p in products if (p.get("availability") or "").lower() != "instock"]
        for base in oos[:30]:
            # find 3 alternatives
            scores = []
            for alt in instock:
                s = fuzz.token_set_ratio(base.get("name") or "", alt.get("name") or "")
                scores.append((s, alt))
            scores.sort(reverse=True, key=lambda x: x[0])
            picks = []
            for s, alt in scores[:6]:
                picks.append({
                    "name": alt.get("name") or "Alternative",
                    "url": alt["url"],
                    "price": f"${alt['price']}" if alt.get("price") and not str(alt["price"]).startswith("$") else alt.get("price"),
                    "merchant": "",
                    "reason": pick_reason(base, alt)
                })
            if picks:
                items.append({
                    "original_name": base.get("name") or "Original Product",
                    "original_url": base["url"],
                    "status": "oos",
                    "slug": slugify((base.get("name") or "original")[:80]),
                    "explanation": "Refreshed alternatives based on current availability and price.",
                    "alternatives": picks[:6]
                })

        if items:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                CHUNK = 25
                for i in range(0, len(items), CHUNK):
                    batch = {"items": items[i:i+CHUNK]}
                    r = await client.post(TPP_ENDPOINT, headers={
                        "Content-Type":"application/json",
                        "X-TPP-Secret":TPP_SECRET
                    }, json=batch)
                    print("REFRESH POST", i, r.status_code, r.text[:200])

    finally:
        await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
