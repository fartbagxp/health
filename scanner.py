#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
from email.mime import text
import logging
import requests
import re

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(levelname)s - %(message)s",
  handlers=[logging.StreamHandler(), logging.FileHandler("cdc_wonder_dmap.log")]
)
log = logging.getLogger("wonder-dmap")

BASE = "https://wonder.cdc.gov"
CTRL = f"{BASE}/controller/datarequest"

HEADERS = {
  "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def is_wonder_html(url: str) -> bool:
  try:
    u = urlparse(url)
  except Exception:
    return False
  if not (u.scheme and u.netloc):
    return False
  return u.netloc.lower() == urlparse(BASE).netloc.lower() and u.path.lower().endswith(".html")

def extract_years(text: str) -> str:
  if not text:
    return ""
  
  # Find all 4-digit numbers and filter to 1900-2500 range
  years = re.findall(r'\d{4}', text)
  valid_years = [year for year in years if 1900 <= int(year) <= 2500]
  
  if not valid_years:
    return ""
  
  # Remove duplicates and sort
  unique_years = sorted(set(valid_years))
  
  # Return single year or range
  if len(unique_years) == 1:
    return unique_years[0]
  else:
    return f"{unique_years[0]}-{unique_years[-1]}"

def html_redirect_candidates(html: str, base_url: str) -> list[str]:
  """Find .html targets in meta refresh, JS redirects, and <a href> links."""
  out: list[str] = []
  soup = BeautifulSoup(html, "html.parser")

  # <meta http-equiv="refresh" content="0;url=/something.html">
  for meta in soup.find_all("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"}):
    content = meta.get("content", "") or meta.get("CONTENT", "")
    m = re.search(r'url\s*=\s*([^;]+)', content, flags=re.I)
    if m:
      out.append(urljoin(base_url, m.group(1).strip().strip('\'"')))

  # JS redirects: window.location = "...", document.location = "...", location.href = "..."
  js_patterns = [
    r'window\.location\s*=\s*([\'"])(.+?)\1',
    r'document\.location\s*=\s*([\'"])(.+?)\1',
    r'location\.href\s*=\s*([\'"])(.+?)\1',
    r'location\.replace\(\s*([\'"])(.+?)\1\s*\)',
  ]
  for pat in js_patterns:
    for m in re.finditer(pat, html, flags=re.I):
      out.append(urljoin(base_url, m.group(2).strip()))

  # Anchor links
  for a in soup.find_all("a", href=True):
    href = a["href"].strip()
    if href and not href.lower().startswith(("javascript:", "#")):
      out.append(urljoin(base_url, href))

  # Keep only wonder .html and dedupe preserving order
  seen = set()
  filtered = []
  for u in out:
    if is_wonder_html(u) and u not in seen:
      seen.add(u)
      filtered.append(u)
  return filtered

def pick_best_html(candidates: list[str], fallback: str | None = None) -> str:
  """Pick a reasonable .html: prefer shortest path and DB keywords, 
  but skip known irrelevant pages (e.g., faq.html)."""
  if not candidates:
    return fallback or ""

  ignore_patterns = (
    "faq.html",  # skip FAQ
    "main.html"
  )

  filtered = [u for u in candidates if not any(p in u.lower() for p in ignore_patterns)]
  if not filtered:
    # if everything was ignored, fall back
    return fallback or ""

  # Bias by common database words
  priority_words = ("sql", "icd10", "natality", "mort", "bridged", "birth", "ucd", "cmf", "mcd")
  scored = []
  for u in filtered:
    path = urlparse(u).path.lower()
    score = sum(1 for w in priority_words if w in path)
    scored.append((score, len(path), u))
  scored.sort(key=lambda x: (-x[0], x[1], x[2]))
  return scored[0][2]

def probe_d_id(dnum: int, session: requests.Session | None = None, delay_sec: float = 0.25) -> dict:
  sid = f"D{dnum}"
  ctrl = f"{BASE}/controller/datarequest/{sid}"
  s = session or requests.Session()
  row = {
    "id": sid,
    "controller_url": ctrl,
    "http_status": "",
    "discovery": "",
    "final_url": "",
    "page_name": "",
    "years": "",
    "error": ""
  }
  try:
    r = s.get(ctrl, timeout=15, allow_redirects=True)
    row["http_status"] = str(r.status_code)

    # Collect redirect-related candidates from history and headers
    candidates: list[str] = []

    # History locations
    for h in r.history:
      loc = h.headers.get("Location", "")
      if loc:
        candidates.append(urljoin(h.url, loc))

    # Final response's Location (in case allow_redirects=False in future)
    loc = r.headers.get("Location", "")
    if loc:
      candidates.append(urljoin(r.url, loc))

    # Always consider r.url itself if .html
    if is_wonder_html(r.url):
      candidates.append(r.url)

    # If server returned HTML (even with 500), parse it to mine candidates
    content_type = r.headers.get("Content-Type", "")
    if "text/html" in content_type and r.text:
      mined = html_redirect_candidates(r.text, r.url)
      if mined:
        log.info(f"[{sid}] mined .html candidates from HTML: {mined}")
      candidates.extend(mined)

    # Filter candidates to wonder .html and dedupe
    dedup = []
    seen = set()
    for u in candidates:
      if is_wonder_html(u) and u not in seen:
        seen.add(u)
        dedup.append(u)

    log.info(f"[{sid}] status={r.status_code} ctrl={ctrl}")
    if dedup:
      log.info(f"[{sid}] .html candidates: {dedup}")

    # Choose the “best” .html; fall back to r.url if it’s .html
    chosen = pick_best_html(dedup, fallback=r.url if is_wonder_html(r.url) else None)

    if chosen:
      row["final_url"] = chosen
      row["page_name"] = urlparse(chosen).path.rsplit("/", 1)[-1]
      row["discovery"] = "redirect" if chosen.rstrip("/") != ctrl.rstrip("/") else "direct"
      row["years"] = extract_years(row["page_name"])
      log.info(f"[{sid}] CHOSEN .html: {chosen}")
    else:
      # No .html found — keep mapping info anyway
      row["discovery"] = "direct" if r.status_code == 200 else f"http_{r.status_code}"
      log.warning(f"[{sid}] no .html found; r.url={r.url}")

  except requests.RequestException as e:
    row["http_status"] = "error"
    row["discovery"] = "error"
    row["error"] = str(e)
    log.error(f"[{sid}] request error: {e}")

  # polite pause
  import time as _t
  _t.sleep(delay_sec)
  return row

def map_d_range(start: int = 1, end: int = 200, out_csv: str = "cdc_wonder_dmap.csv") -> list[dict]:
  sess = requests.Session()
  sess.headers.update(HEADERS)
  rows = []
  for n in range(start, end + 1):
    row = probe_d_id(n, session=sess)
    rows.append(row)
    status = row["discovery"]
    final_url = row["final_url"] or "-"
    log.info(f"{row['id']}: {status:>10}  {final_url}")
    if n % 20 == 0:
      log.info(f"...progress {n - start + 1}/{end - start + 1}")

  cols = ["id", "controller_url", "http_status", "discovery", "final_url", "page_name", "years", "error"]
  with open(out_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
      w.writerow({k: r.get(k, "") for k in cols})
  log.info(f"Wrote {len(rows)} rows to {out_csv}")
  return rows

if __name__ == "__main__":
  map_d_range(1, 200)
