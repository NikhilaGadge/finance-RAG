"""Download earnings press releases (8-K, Item 2.02, Exhibit 99.1) from SEC EDGAR."""

import json
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

TICKERS = ["BLK", "STT", "TROW", "IVZ", "BEN"]
START_DATE = "2023-01-01"
END_DATE = "2025-12-31"
FORM_TYPE = "8-K"
ITEM = "2.02"          # earnings releases
OUT_DIR = Path("data/raw")

USER_AGENT = os.getenv("SEC_USER_AGENT")
"""
if not USER_AGENT:
    raise RuntimeError("SEC_USER_AGENT missing - add 'Your Name your@email.com' to .env")
"""
HEADERS = {"User-Agent": USER_AGENT}


"""
Example of a press release URL on the SEC website:

https://www.sec.gov/Archives/edgar/data/2012383/000095017024114208/blk-ex99_1.htm
                                        └──┬──┘ └───────┬────────┘ └─────┬─────┘
                                       company       filing ID       file name
                                        (CIK)      (accession no.)


2012383, the company ID --> ticker_to_cik() turns “BLK” into this
000095017024114208, the filing ID --> iter_filings()
blk-ex99_1.htm, the press release file --> find_press_release_url()                                        
"""

def get(url):
    """Download a URL, politely: the SEC allows max 10 requests per second."""
    time.sleep(0.15)
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response


def ticker_to_cik():
    """Map tickers (e.g. 'BLK') to SEC company IDs (CIKs) and company names."""
    data = get("https://www.sec.gov/files/company_tickers.json").json()
    # Build a dictionary like {"BLK": ("0002012383", "BlackRock, Inc."), ...}
    # zfill(10) pads the CIK with zeros to 10 digits, because the SEC URLs need that format
    return {row["ticker"]: (str(row["cik_str"]).zfill(10), row["title"]) for row in data.values()}


# HELPER 3: list all filings of one company

def iter_filings(cik):
    """Yield every filing of a company: recent ones plus older archive pages."""
    base = "https://data.sec.gov/submissions/"                # SEC's API for a company's filing history
    sub = get(f"{base}CIK{cik}.json").json()                  # download the company's filing list
    blocks = [sub["filings"]["recent"]]                       # start with the most recent filings
    # Older filings are split into extra pages ("files"); go through them too
    for page in sub["filings"].get("files", []):
        if page["filingTo"] < START_DATE:                     # this page ends before our start date ...
            continue                                          # ... so skip it, nothing useful there
        blocks.append(get(base + page["name"]).json())        # otherwise download that page as well
    # The SEC stores data in columns (all forms, all dates, ...); turn it into one dict per filing
    for block in blocks:
        n = len(block["form"])                                # number of filings in this block
        items = block.get("items", [""] * n)                  # 8-K item numbers (e.g. "2.02,9.01"); empty if missing
        for i in range(n):                                    # go through filing number 0, 1, 2, ...
            yield {                                           # "yield" hands out one filing at a time
                "form": block["form"][i],                     # form type, e.g. "8-K", "10-Q"
                "date": block["filingDate"][i],               # filing date, e.g. "2024-10-11"
                "accession": block["accessionNumber"][i],     # unique ID of this filing
                "items": items[i] or "",                      # which 8-K items it reports ("" if none)
            }

def find_press_release_url(cik, accession):
    """Open the filing's index page and return the link to its Exhibit 99 document."""
    acc_nodash = accession.replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodash}/{accession}-index.htm"
    soup = BeautifulSoup(get(index_url).text, "html.parser")
    for row in soup.select("table.tableFile tr"):
        cells = row.find_all("td")
        # columns: Seq | Description | Document | Type | Size
        if len(cells) >= 4 and cells[3].get_text(strip=True).upper().startswith("EX-99"):
            link = cells[2].find("a")
            if link:
                return "https://www.sec.gov" + link["href"].replace("/ix?doc=", "")
    return None


def html_to_text(html):
    """Strip HTML tags and tidy whitespace."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    lines = [re.sub(r"\s+", " ", line).strip() for line in soup.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ciks = ticker_to_cik()
    records = []

    for ticker in TICKERS:
        cik, company = ciks[ticker]
        count = 0
        for f in iter_filings(cik):
            # 8-K with Item 2.02 = "Results of Operations" = earnings release
            if f["form"] != FORM_TYPE or ITEM not in f["items"]:
                continue
            if not (START_DATE <= f["date"] <= END_DATE):
                continue

            url = find_press_release_url(cik, f["accession"])
            if url is None:
                print(f"  ! no press release found in {ticker} {f['date']}")
                continue

            text = html_to_text(get(url).text)
            filename = f"{ticker}_{f['date']}.txt"
            (OUT_DIR / filename).write_text(text, encoding="utf-8")
            records.append({
                "file": filename,
                "ticker": ticker,
                "company": company,
                "date": f["date"],
                "url": url,
            })
            count += 1

        print(f"{ticker} ({company}): {count} press releases")

    with open(OUT_DIR / "metadata.jsonl", "w", encoding="utf-8") as out:
        for record in records:
            out.write(json.dumps(record) + "\n")
    print(f"Done: {len(records)} press releases saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()