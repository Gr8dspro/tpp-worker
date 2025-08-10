#!/usr/bin/env python3
import os, json, time
import requests

# === SET THESE ===
ENDPOINT = os.environ.get("TPP_ENDPOINT", "https://toppickspilot.com/wp-json/tpp/v1/ingest")
SECRET   = os.environ.get("TPP_SECRET", "RfMghvZIiDh45NfXWMAownPgqwwTorJV")  # Or set env var TPP_SECRET

payload = {
  "items": [
    {
      "original_name": "Acme Widget 3000",
      "original_url": "https://example.com/acme-widget-3000",
      "status": "discontinued",
      "slug": "acme-widget-3000",
      "explanation": "Closest current models with similar capacity and price.",
      "alternatives": [
        {
          "name": "Acme Widget 4000",
          "url": "https://www.bestbuy.com/site/placeholder/000000.p",
          "price": "$129",
          "merchant": "Best Buy",
          "reason": "Newer model; same accessories"
        },
        {
          "name": "Contoso Widget Pro",
          "url": "https://www.walmart.com/ip/placeholder/000000",
          "price": "$119",
          "merchant": "Walmart",
          "reason": "Cheaper; similar spec"
        },
        {
          "name": "Globex Widget Lite",
          "url": "https://www.amazon.com/dp/B000000000",
          "price": "$99",
          "merchant": "Amazon",
          "reason": "Budget alternative"
        }
      ]
    }
  ]
}

headers = {
  "Content-Type": "application/json",
  "X-TPP-Secret": SECRET
}

print("Posting 1 sample page to:", ENDPOINT)
r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=30)
print("Status:", r.status_code)
print("Response:", r.text)
