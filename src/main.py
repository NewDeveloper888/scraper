from datetime import datetime, timezone
import json
from fetcher import fetch_page
from models import RawBookRecord
from parser import extract_book_details, extract_book_links, extract_next_page_url


def discover_books(start_url: str, max_pages: int = 3) -> list[tuple[str, str]]:
    """
    Crawl through catalogue pages and return a list of tuples: (book_url, source_page_url).
    """
    current_url = start_url
    pages_crawled = 0
    discovered: list[tuple[str, str]] = []

    while current_url and pages_crawled < max_pages:
        pages_crawled += 1
        cache_name = f"catalogue-page-{pages_crawled}"

        html_content, _ = fetch_page(current_url, custom_cache_name=cache_name)
        if not html_content:
            break

        links = extract_book_links(html_content, base_url=current_url)
        for link in links:
            discovered.append((link, current_url))

        if pages_crawled < max_pages:
            current_url = extract_next_page_url(html_content, base_url=current_url)
        else:
            current_url = None

    # Deduplicate by book URL
    seen_urls = set()
    unique_items = []
    for url, src in discovered:
        if url not in seen_urls:
            seen_urls.add(url)
            unique_items.append((url, src))

    return unique_items


def main():
    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    print("Stage 3: Extracting book details...")

    book_entries = discover_books(start_url, max_pages=3)
    raw_records: list[RawBookRecord] = []

    for book_url, source_page in book_entries:
        # Fetch individual book detail page (cached automatically by URL hash)
        html_content, _ = fetch_page(book_url)
        if not html_content:
            continue

        now_iso = datetime.now(timezone.utc).isoformat()
        raw_dict = extract_book_details(
            html_content=html_content,
            product_url=book_url,
            source_page=source_page,
            fetched_at=now_iso,
        )

        record = RawBookRecord(**raw_dict)
        raw_records.append(record)

    # Checkpoint output
    print(f"\ndetail_pages={len(raw_records)}")
    if raw_records:
        print("\n--- Sample Raw Record ---")
        print(json.dumps(raw_records[0].model_dump(), indent=2))


if __name__ == "__main__":
    main()