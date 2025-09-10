#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import csv
import time
import logging
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(levelname)s - %(message)s",
  handlers=[logging.StreamHandler(), logging.FileHandler("cdc_wonder_link_harvest.log")]
)
log = logging.getLogger("wonder-harvest")

BASE = "https://wonder.cdc.gov"

HEADERS = {
  "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def is_wonder_html(url: str) -> bool:
  try:
    u = urlparse(url)
  except Exception:
    return False
  if not u.scheme or not u.netloc:
    return False
  if u.netloc.lower() != urlparse(BASE).netloc.lower():
    return False
  return u.path.lower().endswith(".html")

def normalize(url: str, base: str) -> str:
  return urljoin(base, url)

def extract_years(text: str) -> str:
  if not text:
    return ""
  m = re.search(r'(\d{4})\s*[-–]\s*(\d{4})', text)
  if m:
    return f"{m.group(1)}-{m.group(2)}"
  years = re.findall(r'\b(19[5-9]\d|20[0-4]\d|2050)\b', text)
  if years:
    years = sorted(set(years))
    return years[0] if len(years) == 1 else f"{years[0]}-{years[-1]}"
  return ""

def fetch(url: str, timeout: int = 15) -> requests.Response | None:
  try:
    r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
      return r
    log.debug(f"Skip non-HTML or status {r.status_code}: {url}")
  except requests.RequestException as e:
    log.debug(f"Fetch error for {url}: {e}")
  return None

def page_title(html: str) -> str:
  try:
    soup = BeautifulSoup(html, "html.parser")
    t = soup.find("title")
    if t and t.text:
      title = t.text.strip()
      for s in [" on CDC WONDER", " - CDC WONDER", " Request", " Request Form"]:
        title = title.replace(s, "")
      return title.strip()
    h1 = soup.find("h1")
    return h1.text.strip() if h1 else ""
  except Exception:
    return ""

def extract_links(html: str, current_url: str) -> list[str]:
  out = []
  soup = BeautifulSoup(html, "html.parser")
  for a in soup.find_all("a", href=True):
    href = a["href"].strip()
    if href.startswith("#") or href.lower().startswith("javascript:"):
      continue
    abs_url = normalize(href, current_url)
    if is_wonder_html(abs_url):
      out.append(abs_url)
  return out

def crawl(
  seeds: list[str],
  max_pages: int = 50,
  same_host_only: bool = True,
  delay_sec: float = 0.3
) -> list[dict]:
  seen_pages = set()
  queue = deque(seeds)
  results = {}
  host = urlparse(BASE).netloc.lower()

  while queue and len(seen_pages) < max_pages:
    url = queue.popleft()
    if url in seen_pages:
      continue
    if same_host_only and urlparse(url).netloc.lower() != host:
      continue

    log.info(f"Fetching page: {url}")
    resp = fetch(url)
    seen_pages.add(url)
    if not resp:
      continue

    title = page_title(resp.text)
    for link in extract_links(resp.text, url):
      if link not in results:
        years = extract_years(link) or extract_years(title)
        path = urlparse(link).path.rsplit("/", 1)[-1]
        results[link] = {
          "url": link,
          "page_name": path,
          "title": title,
          "years": years,
          "source_url": url,
        }
      # Optionally follow discovered html pages too (light spidering)
      if same_host_only and link not in seen_pages and len(seen_pages) + len(queue) < max_pages:
        queue.append(link)

    time.sleep(delay_sec)

  return list(results.values())

def write_csv(rows: list[dict], out_path: str = "cdc_wonder_links.csv") -> None:
  if not rows:
    log.warning("No rows to write.")
    return
  # Sort rows by URL before writing
  sorted_rows = sorted(rows, key=lambda x: x.get("url", ""))
  cols = ["url", "page_name", "title", "years", "source_url"]
  with open(out_path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in sorted_rows:
      w.writerow({k: r.get(k, "") for k in cols})
  log.info(f"Wrote {len(rows)} rows to {out_path}")

def main():
  seeds = [
    BASE + "/",                     # homepage
    BASE + "/welcomet.html",        # topics
    BASE + "/welcomea.html",        # A-Z index
    BASE + "/about.html",           # common hub
    BASE + "/data.html",            # data hub
    BASE + "/mortSQL.html",         # example entry
  ]
  rows = crawl(seeds=seeds, max_pages=120, same_host_only=True, delay_sec=0.25)
  write_csv(rows, "cdc_wonder_links.csv")

if __name__ == "__main__":
  main()
