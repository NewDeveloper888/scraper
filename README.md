<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Polite Scraper — Architecture, Design & Implementation Guide</title>
</head>
<body>

<h1>The Polite Scraper — Architecture, Design &amp; Implementation Guide</h1>

<p><em>FlyRank Backend Track · Week 5 · Assignment A9</em></p>

<p>
A production-grade, deterministic, and resilient web scraping pipeline built with
<strong>Python 3.10+</strong>, <strong>BeautifulSoup4</strong>, and <strong>Pydantic V2</strong>.
</p>

<hr>

<h2>1. Project Overview &amp; Guiding Philosophy</h2>

<p>
The purpose of this pipeline is to extract structured, schema-validated product data
from the public sandbox <strong>Books to Scrape</strong>, visiting 60 product detail
pages across 3 catalogue pages.
</p>

<p>
Modern automated data collection is not merely about pulling HTML markup; it is an
engineering discipline requiring three core tenets:
</p>

<ol>
  <li>
    <strong>Check Before You Collect:</strong>
    Classify permissions, read robots exclusion rules, and define strict operational
    boundaries before sending a single HTTP packet.
  </li>
  <li>
    <strong>Be a Polite Guest:</strong>
    Respect server resources through strict rate-limiting, local caching during
    development, explicit client identification (<code>User-Agent</code>), and
    fast-fail strategies.
  </li>
  <li>
    <strong>Trust Nothing You Scraped:</strong>
    Treat web markup as untrusted input by running raw data through schema validators,
    normalizers, and idempotent persistent storage.
  </li>
</ol>

<hr>

<h2>2. Target Classification &amp; Scope</h2>

<ul>
  <li><strong>Target URL:</strong> <code>https://books.toscrape.com</code></li>

  <li>
    <strong>Target Purpose:</strong>
    A public sandbox specifically hosted for testing, learning, and benchmarking
    web scrapers safely.
  </li>

  <li>
    <strong>Scope Boundary:</strong>
    Exactly the first 3 catalogue index pages (60 distinct books total).
  </li>

  <li>
    <strong>Robots Policy Inspection:</strong>
    A preliminary request to
    <code>https://books.toscrape.com/robots.txt</code>
    yields an HTTP <code>404 Not Found</code>. While a missing
    <code>robots.txt</code> does not imply explicit carte blanche, the host page
    explicitly declares itself an open scraping sandbox.
  </li>

  <li>
    <strong>Ethical Commitment:</strong>
    I will not reuse this code on any target system without prior analysis of its
    Terms of Service, rate constraints, and robots exclusion rules.
  </li>
</ul>

<hr>

<h2>3. Pipeline Architecture &amp; Data Flow</h2>

<p>
The scraping engine is built as an end-to-end deterministic pipeline:
</p>

<pre><code>[Target URL]
     │
     ▼
[Step 1: Fetch &amp; Cache] ──── (Cache Hit?) ──► Read local disk (cache/*.html)
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
[Step 4: Normalization &amp; Validation]
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
</code></pre>

<hr>

<h2>4. Engineering Pillars Explained</h2>

<h3>A. Provenance (Data Lineage)</h3>

<p>Every single record retains its exact source of origin:</p>

<ul>
  <li>
    <code>source_page</code>: The index page URL where the item was discovered.
  </li>
  <li>
    <code>fetched_at</code>: An immutable ISO 8601 UTC timestamp of the exact time
    the markup was fetched.
  </li>
  <li>
    <em>Why it matters:</em>
    In production pipelines, data anomalies must be traceable back to the raw source
    and exact retrieval window.
  </li>
</ul>

<h3>B. Idempotency</h3>

<p>
Running the pipeline multiple times produces the exact same deterministic dataset
(60 validated records) without multiplying rows or introducing state collisions.
</p>

<h3>C. Fault Tolerance &amp; Isolated Page Failures</h3>

<p>
A failed detail page (e.g., HTTP 404, malformed DOM tree, broken selector) does not
crash the runtime. The engine catches the exception, logs the event to
<code>output/errors.json</code>, increments <code>failed_pages</code>, and continues
processing remaining items.
</p>

<h3>D. Headless vs. Browser-Free Execution</h3>

<p>
Plain HTTP requests (<code>requests</code> + <code>BeautifulSoup</code>) are used
rather than heavy browser automation tools (Playwright / Puppeteer). The markup is
fully pre-rendered on the server (SSR); running a full browser engine would only
introduce unnecessary memory footprint and CPU overhead.
</p>

<hr>

<h2>5. Directory Structure</h2>

<pre><code>scraper/
├── cache/                  # Ignored by git; stores raw HTML dumps by URL hash
├── output/                 # Pipeline output artifacts
│   ├── books.json          # 60 validated, canonical records
│   ├── errors.json         # Segregated malformed/failed records
│   └── run-report.json     # Execution metrics and telemetry
├── src/
│   ├── __init__.py
│   ├── fetcher.py          # HTTP transport, polite throttling, disk caching, retry logic
│   ├── parser.py           # BeautifulSoup DOM queries, pagination, and relative URL resolution
│   ├── models.py           # Pydantic schemas (RawBookRecord &amp; NormalizedBookRecord)
│   ├── storage.py          # Atomic file writes and idempotent JSON persistence
│   └── main.py             # Orchestration entry point and error injection test harness
├── .gitignore
├── requirements.txt
└── README.md
</code></pre>

<hr>

<h2>6. Data Schemas</h2>

<h3>Raw Record Schema</h3>

<p>Captures unaltered, literal strings from the DOM:</p>

<p>Python</p>

<pre><code>class RawBookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str
</code></pre>

<h3>Normalized &amp; Validated Schema</h3>

<p>Enforces strict type safety and URL validity:</p>

<p>Python</p>

<pre><code>class NormalizedBookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: HttpUrl
    fetched_at: str
</code></pre>

<hr>

<h2>7. How to Build This Scraper From Scratch (Step-by-Step)</h2>

<p>
If you are recreating this pipeline from a clean slate, execute the following
implementation order:
</p>

<h3>Stage 0 — Setup &amp; Classification</h3>

<ol>
  <li>
    Initialize repository with <code>.gitignore</code>
    (ignoring <code>cache/</code>, <code>venv/</code>, and
    <code>__pycache__/</code>).
  </li>
  <li>
    Verify target permissions and verify <code>robots.txt</code>.
  </li>
</ol>

<h3>Stage 1 — The Polite Fetcher (<code>src/fetcher.py</code>)</h3>

<ol>
  <li>
    Implement disk caching: hash target URLs (e.g., using <code>md5</code>)
    and store contents in <code>cache/&lt;hash&gt;.html</code>.
  </li>
  <li>
    Configure default headers with a clear
    <code>User-Agent: FlyRankInternship-A9/1.0 (+&lt;repo_url&gt;)</code>.
  </li>
  <li>
    Wrap network calls with <code>timeout=5</code> and insert an unconditional
    <code>time.sleep(0.5)</code> throttle before live network calls.
  </li>
</ol>

<h3>Stage 2 — Discovery &amp; Absolute URLs (<code>src/parser.py</code>)</h3>

<ol>
  <li>
    Use <code>BeautifulSoup(html, "html.parser")</code> to parse catalogue pages.
  </li>
  <li>
    Select book elements
    (<code>article.product_pod h3 a</code>).
  </li>
  <li>
    Resolve relative <code>href</code> attributes to absolute URLs using
    <code>urllib.parse.urljoin(current_url, href)</code>.
  </li>
  <li>
    Follow pagination (<code>li.next a</code>) dynamically up to page 3.
  </li>
</ol>

<h3>Stage 3 — DOM Extraction</h3>

<ol>
  <li>
    Query individual product nodes: title (<code>h1</code>),
    price (<code>p.price_color</code>),
    availability (<code>p.instock.availability</code>), and
    rating (<code>p.star-rating</code>).
  </li>
  <li>
    Return a strict raw dictionary containing provenance metadata
    (<code>source_page</code>, <code>fetched_at</code>).
  </li>
</ol>

<h3>Stage 4 — Normalization &amp; Validation (<code>src/models.py</code>)</h3>

<ol>
  <li>
    Extract numeric values from currency strings using Regex
    (<code>\d+\.\d+</code>).
  </li>
  <li>
    Pass normalized dicts through <code>NormalizedBookRecord</code> (Pydantic).
  </li>
  <li>
    Route validation failures to <code>output/errors.json</code> and successes to
    <code>output/books.json</code>.
  </li>
</ol>

<h3>Stage 5 — Error Handling &amp; Telemetry (<code>src/main.py</code>)</h3>

<ol>
  <li>
    Implement retry rules: Retry once on <code>5xx</code> or
    <code>Timeout</code>; fail immediately on <code>404</code> or
    <code>403</code>.
  </li>
  <li>
    Wrap per-book processing in <code>try/except</code> blocks.
  </li>
  <li>
    Track run telemetry
    (<code>cache_hits</code>, <code>network_fetches</code>,
    <code>duration_seconds</code>) and write
    <code>output/run-report.json</code>.
  </li>
</ol>

<hr>

<h2>8. Installation &amp; Quickstart</h2>

<h3>Prerequisites</h3>

<ul>
  <li>Python 3.10 or higher</li>
  <li>Git</li>
</ul>

<h3>Step-by-Step Setup</h3>

<ol>
  <li>
    <strong>Clone the repository:</strong>

    <p>Bash</p>

    <pre><code>git clone https://github.com/NewDeveloper888/scraper.git
cd scraper</code></pre>
  </li>

  <li>
    <strong>Create and activate a virtual environment:</strong>

    <h4>Windows (PowerShell)</h4>

    <pre><code>python -m venv venv
venv\Scripts\Activate.ps1</code></pre>

    <h4>Linux / macOS</h4>

    <pre><code>python3 -m venv venv
source venv/bin/activate</code></pre>
  </li>

  <li>
    <strong>Install dependencies:</strong>

    <pre><code>pip install -r requirements.txt</code></pre>
  </li>

  <li>
    <strong>Execute the pipeline:</strong>

    <pre><code>python src/main.py</code></pre>
  </li>
</ol>

<hr>

<h2>9. Sample Execution Report (<code>output/run-report.json</code>)</h2>

<p>JSON</p>

<pre><code>{
  "start_time": "2026-08-31T12:25:00.000000+00:00",
  "duration_seconds": 1.45,
  "catalogue_pages_crawled": 3,
  "detail_pages_total": 61,
  "cache_hits": 63,
  "network_fetches": 1,
  "valid_records": 60,
  "invalid_records": 1,
  "failed_pages": 1
}</code></pre>

<hr>

<h2>10. Ethics &amp; Operational Boundaries</h2>

<ul>
  <li>
    <strong>Official APIs First:</strong>
    Always query programmatic API endpoints when provided by the vendor before
    turning to DOM scraping.
  </li>

  <li>
    <strong>Authentication &amp; Walls:</strong>
    Never write routines to bypass CAPTCHA, authentication screens, or paywalls.
  </li>

  <li>
    <strong>Resource Conservation:</strong>
    Always enforce strict rate limiting and cache raw artifacts locally during
    development.
  </li>

  <li>
    <strong>Known System Limitation:</strong>
    Selectors are coupled to the static server-side HTML layout of Books to Scrape.
    If client-side hydration or a responsive template rewrite occurs, extraction
    rules must be updated accordingly.
  </li>
</ul>

</body>
</html>
