import hashlib
import time
from pathlib import Path
import requests

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Identify the scraper politely with a repo contact link
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/your-username/scraper)"
}
TIMEOUT = 5  # Give up after 5 seconds instead of hanging


def get_cache_path(url: str, custom_name: str | None = None) -> Path:
    """Return a cache file path using a custom name or a hashed URL."""
    if custom_name:
        return CACHE_DIR / f"{custom_name}.html"
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{url_hash}.html"


def fetch_page(
    url: str, custom_cache_name: str | None = None, delay: float = 0.5
) -> tuple[str, bool]:
    """
    Fetch an HTML page safely:
    - Return cached copy if present.
    - Delay requests to avoid hammering the host.
    - Validate response status code (only 200 is acceptable).
    - Save new HTML to disk for future runs.
    """
    cache_file = get_cache_path(url, custom_cache_name)

    # 1. Read from local cache if we already downloaded it
    if cache_file.exists():
        html_content = cache_file.read_text(encoding="utf-8")
        size_kb = len(html_content.encode("utf-8")) / 1024
        print(f"[CACHE HIT] {url} -> Size: {size_kb:.2f} KB")
        return html_content, True

    # 2. Be polite: pause before hitting the live server
    if delay > 0:
        time.sleep(delay)

    # 3. Perform network request safely
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

        # Only status code 200 is treated as valid HTML
        if response.status_code != 200:
            print(f"[FAILED] {url} -> Status Code: {response.status_code}")
            return "", False

        html_content = response.text
        cache_file.write_text(html_content, encoding="utf-8")
        size_kb = len(html_content.encode("utf-8")) / 1024
        print(f"[FETCH] {url} -> Size: {size_kb:.2f} KB")
        return html_content, False

    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return "", False