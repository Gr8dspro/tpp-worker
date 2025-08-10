import json, re
from bs4 import BeautifulSoup

def extract_product_ld(html: str):
    """Returns a dict with keys: name, price, currency, availability, rating, review_count if available."""
    soup = BeautifulSoup(html, "lxml")
    data = {"name": None, "price": None, "currency": None, "availability": None, "rating": None, "review_count": None}
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            obj = json.loads(tag.string or "")
        except Exception:
            continue
        for node in (obj if isinstance(obj, list) else [obj]):
            if isinstance(node, dict) and node.get("@type") in ("Product", ["Product"]):
                data["name"] = node.get("name") or data["name"]
                offers = node.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0]
                price = offers.get("price")
                currency = offers.get("priceCurrency")
                availability = offers.get("availability")
                if isinstance(availability, str):
                    availability = availability.split("/")[-1]
                agg = node.get("aggregateRating") or {}
                rating = agg.get("ratingValue")
                review_count = agg.get("reviewCount") or agg.get("reviewcount") or agg.get("ratingCount")
                data.update({
                    "price": price, "currency": currency, "availability": availability,
                    "rating": rating, "review_count": review_count
                })
                return data
    # Fallback: try to parse price patterns
    m = re.search(r"\$(\d+[\.,]?\d*)", html)
    if m:
        data["price"] = m.group(0)
    return data
