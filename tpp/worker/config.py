import os, yaml, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG  = yaml.safe_load((ROOT / "merchants.yml").read_text(encoding="utf-8"))

TPP_ENDPOINT = os.environ.get("TPP_ENDPOINT", "").strip()
TPP_SECRET   = os.environ.get("TPP_SECRET", "").strip()

USER_AGENT = "TPPWorker/0.1 (+https://toppickpilot.com)"
MAX_PER_HOST_RPS = 1.5
