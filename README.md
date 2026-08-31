```
```

````
# The Polite Scraper — Architecture, Design & Implementation Guide

*FlyRank Backend Track · Week 5 · Assignment A9*

A production-grade, deterministic, and resilient web scraping pipeline built with **Python 3.10+**, **BeautifulSoup4**, and **Pydantic V2**.

---

## 1. Project Overview & Guiding Philosophy

The purpose of this pipeline is to extract structured, schema-validated product data from the public sandbox **Books to Scrape**, visiting 60 product detail pages across 3 catalogue pages.

Modern automated data collection is not merely about pulling HTML markup; it is an engineering discipline requiring three core tenets:

1. **Check Before You Collect:** Classify permissions, read robots exclusion rules, and define strict operational boundaries before sending a single HTTP packet.
2. **Be a Polite Guest:** Respect server resources through strict rate-limiting, local caching during development, explicit client identification (`User-Agent`), and fast-fail strategies.
3. **Trust Nothing You Scraped:** Treat web markup as untrusted input by running raw data through schema validators, normalizers, and idempotent persistent storage.

---

## 2. Target Classification & Scope

- **Target URL:** `https://books.toscrape.com`
- **Target Purpose:** A public sandbox specifically hosted for testing, learning, and benchmarking web scrapers safely.
- **Scope Boundary:** Exactly the first 3 catalogue index pages (60 distinct books total).
- **Robots Policy Inspection:** A preliminary request to `https://books.toscrape.com/robots.txt` yields an HTTP `404 Not Found`. While a missing `robots.txt` does not imply explicit carte blanche, the host page explicitly declares itself an open scraping sandbox.
- **Ethical Commitment:** I will not reuse this code on any target system without prior analysis of its Terms of Service, rate constraints, and robots exclusion rules.

---

## 3. Pipeline Architecture & Data Flow

The scraping engine is built as an end-to-end deterministic pipeline:

```text
[Target URL]
     │
     ▼
[Step 1: Fetch & Cache] ──── (Cache Hit?) ──► Read local disk (cache/*.html)
     │
     │
     └── (Miss) ──► Wait 500ms ──► HTTP GET with User-Agent + 5s Timeout
                                      │
                                      ▼
                                Save to disk
                                      │
                                      ▼
[Step 2: HTML Parsing] ──► Extract relative URLs ──► urljoin() to Absolute Canonical URLs
                                      │
                                      ▼
[Step 3: Raw Extraction] ──► Extract 8 raw fields + Provenance metadata
                                      │
                                      │
                                      │ source URL + ISO timestamp
                                      ▼
[Step 4: Normalization & Validation]
                    │
                    ├── Regex price extraction (Float)
                    │
                    └── Pydantic Schema checks
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
              (Valid)             (Invalid)
                 │                   │
                 ▼                   ▼
       [output/books.json]   [output/errors.json]
                 │
                 ▼
       [Step 5: Run Telemetry]
                 │
                 ▼
       Aggregate metrics
                 │
                 ▼
       [output/run-report.json]
````

---

## 4. Engineering Pillars Explained

### A. Provenance (Data Lineage)

Every single record retains its exact source of origin:

- `source_page`: The index page URL where the item was discovered. 
- `fetched_at`: An immutable ISO 8601 UTC timestamp of the exact time the markup was fetched. 
- *Why it matters:* In production pipelines, data anomalies must be traceable back to the raw source and exact retrieval window. 

### B. Idempotency

Running the pipeline multiple times produces the exact same deterministic dataset (60 validated records) without multiplying rows or introducing state collisions.

### C. Fault Tolerance & Isolated Page Failures

A failed detail page (e.g., HTTP 404, malformed DOM tree, broken selector) does not crash the runtime. The engine catches the exception, logs the event to `output/errors.json`, increments `failed_pages`, and continues processing remaining items.

### D. Headless vs. Browser-Free Execution

Plain HTTP requests (`requests` + `BeautifulSoup`) are used rather than heavy browser automation tools (Playwright / Puppeteer). The markup is fully pre-rendered on the server (SSR); running a full browser engine would only introduce unnecessary memory footprint and CPU overhead.

---

## 5. Directory Structure

```
```

```
scraper/
├── cache/                  # Ignored by git; stores raw HTML dumps by URL hash
├── output/                 # Pipeline output artifacts
│   ├── books.json          # 60 validated, canonical records
│   ├── errors.json         # Segregated malformed/failed records
│   └── run-report.json     # Execution metrics and telemetry
├── src/
│   ├── __init__.py
│   ├── fetcher.py          # HTTP transport, polite throttling, disk caching, retry logic
│   ├── parser.py           # BeautifulSoup DOM queries, pagination, and relative URL resolution
│   ├── models.py           # Pydantic schemas (RawBookRecord & NormalizedBookRecord)
│   ├── storage.py          # Atomic file writes and idempotent JSON persistence
│   └── main.py             # Orchestration entry point and error injection test harness
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 6. Data Schemas

### Raw Record Schema

Captures unaltered, literal strings from the DOM:

Python

```
```

```
class RawBookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str
```

### Normalized & Validated Schema

Enforces strict type safety and URL validity:

Python

```
```

```
class NormalizedBookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: HttpUrl
    fetched_at: str
```

---

## 7. How to Build This Scraper From Scratch (Step-by-Step)

If you are recreating this pipeline from a clean slate, execute the following implementation order:

### Stage 0 — Setup & Classification

1.  Initialize repository with `.gitignore` (ignoring `cache/`, `venv/`, and `__pycache__/`). 
2.  Verify target permissions and verify `robots.txt`. 

### Stage 1 — The Polite Fetcher (`src/fetcher.py`)

1.  Implement disk caching: hash target URLs (e.g., using `md5`) and store contents in `cache/<hash>.html`. 
2.  Configure default headers with a clear `User-Agent: FlyRankInternship-A9/1.0 (+<repo_url>)`. 
3.  Wrap network calls with `timeout=5` and insert an unconditional `time.sleep(0.5)` throttle before live network calls. 

### Stage 2 — Discovery & Absolute URLs (`src/parser.py`)

1.  Use `BeautifulSoup(html, "html.parser")` to parse catalogue pages. 
2.  Select book elements (`article.product_pod h3 a`). 
3.  Resolve relative `href` attributes to absolute URLs using `urllib.parse.urljoin(current_url, href)`. 
4.  Follow pagination (`li.next a`) dynamically up to page 3. 

### Stage 3 — DOM Extraction

1.  Query individual product nodes: title (`h1`), price (`p.price_color`), availability (`p.instock.availability`), and rating (`p.star-rating`). 
2.  Return a strict raw dictionary containing provenance metadata (`source_page`, `fetched_at`). 

### Stage 4 — Normalization & Validation (`src/models.py`)

1.  Extract numeric values from currency strings using Regex (`\d+\.\d+`). 
2.  Pass normalized dicts through `NormalizedBookRecord` (Pydantic). 
3.  Route validation failures to `output/errors.json` and successes to `output/books.json`. 

### Stage 5 — Error Handling & Telemetry (`src/main.py`)

1.  Implement retry rules: Retry once on `5xx` or `Timeout`; fail immediately on `404` or `403`. 
2.  Wrap per-book processing in `try/except` blocks. 
3.  Track run telemetry (`cache_hits`, `network_fetches`, `duration_seconds`) and write `output/run-report.json`. 

---

## 8. Installation & Quickstart

### Prerequisites

-  Python 3.10 or higher 
-  Git 

### Step-by-Step Setup

1. **Clone the repository:**

   Bash
   ```
   ```
   ```
   git clone https://github.com/NewDeveloper888/scraper.git
   cd scraper
   ```
2. **Create and activate a virtual environment:**
   #### Windows (PowerShell)
   ```
   ```
   ```
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```
   #### Linux / macOS
   ```
   ```
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```
   ```
   ```
   pip install -r requirements.txt
   ```
4. **Execute the pipeline:**
   ```
   ```
   ```
   python src/main.py
   ```

---

## 9. Sample Execution Report (`output/run-report.json`)

JSON

```
```

```
{
  "start_time": "2026-08-31T12:25:00.000000+00:00",
  "duration_seconds": 1.45,
  "catalogue_pages_crawled": 3,
  "detail_pages_total": 61,
  "cache_hits": 63,
  "network_fetches": 1,
  "valid_records": 60,
  "invalid_records": 1,
  "failed_pages": 1
}
```

---

## 10. Ethics & Operational Boundaries

- **Official APIs First:** Always query programmatic API endpoints when provided by the vendor before turning to DOM scraping. 
- **Authentication & Walls:** Never write routines to bypass CAPTCHA, authentication screens, or paywalls. 
- **Resource Conservation:** Always enforce strict rate limiting and cache raw artifacts locally during development. 
- **Known System Limitation:** Selectors are coupled to the static server-side HTML layout of Books to Scrape. If client-side hydration or a responsive template rewrite occurs, extraction rules must be updated accordingly. 

```
```

```
```
.