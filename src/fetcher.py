import hashlib
import time
from pathlib import Path
import requests

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/NewDeveloper888/scraper)"
}
TIMEOUT = 5


def get_cache_path(url: str, custom_name: str | None = None) -> Path:
    """Return a cache file path using a custom name or a hashed URL."""
    if custom_name:
        return CACHE_DIR / f"{custom_name}.html"
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{url_hash}.html"


def fetch_page(
    url: str, custom_cache_name: str | None = None, delay: float = 0.5
) -> tuple[str, bool]:
    """Fetch an HTML page safely with caching, politeness, and single retry on 5xx/Timeout."""
    cache_file = get_cache_path(url, custom_cache_name)

    if cache_file.exists():
        html_content = cache_file.read_text(encoding="utf-8")
        size_kb = len(html_content.encode("utf-8")) / 1024
        print(f"[CACHE HIT] {url} -> Size: {size_kb:.2f} KB")
        return html_content, True

    if delay > 0:
        time.sleep(delay)

    # Attempt up to 2 times for 5xx errors or timeouts
    for attempt in range(1, 3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

            # Success
            if response.status_code == 200:
                html_content = response.text
                cache_file.write_text(html_content, encoding="utf-8")
                size_kb = len(html_content.encode("utf-8")) / 1024
                print(f"[FETCH] {url} -> Size: {size_kb:.2f} KB")
                return html_content, False

            # Do not retry on client errors like 404 or 403
            if response.status_code in (404, 403):
                print(
                    f"[FAILED - NO RETRY] {url} -> Status Code: {response.status_code}"
                )
                return "", False

            # Retry once on 5xx server errors
            if response.status_code >= 500 and attempt == 1:
                print(
                    f"[SERVER ERROR {response.status_code}] Retrying {url} in 1s..."
                )
                time.sleep(1.0)
                continue

            print(f"[FAILED] {url} -> Status Code: {response.status_code}")
            return "", False

        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt == 1:
                print(f"[TIMEOUT/ERROR] Retrying {url} in 1s... ({e})")
                time.sleep(1.0)
                continue
            print(f"[ERROR] Failed after retry {url}: {e}")
            return "", False
        except requests.RequestException as e:
            print(f"[ERROR] Request failed for {url}: {e}")
            return "", False

    return "", False