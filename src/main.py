from datetime import datetime, timezone
from pydantic import ValidationError
from fetcher import fetch_page
from models import NormalizedBookRecord, RawBookRecord
from parser import extract_book_details, extract_book_links, extract_next_page_url
from storage import save_json_records


def discover_books(start_url: str, max_pages: int = 3) -> list[tuple[str, str]]:
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

    seen_urls = set()
    unique_items = []
    for url, src in discovered:
        if url not in seen_urls:
            seen_urls.add(url)
            unique_items.append((url, src))

    return unique_items


def main():
    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    print("Stage 4: Normalizing, validating, and storing records...")

    book_entries = discover_books(start_url, max_pages=3)

    valid_records: list[NormalizedBookRecord] = []
    error_records: list[dict] = []

    for book_url, source_page in book_entries:
        html_content, _ = fetch_page(book_url)
        if not html_content:
            error_records.append(
                {"url": book_url, "reason": "Failed to fetch HTML"}
            )
            continue

        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            raw_dict = extract_book_details(
                html_content=html_content,
                product_url=book_url,
                source_page=source_page,
                fetched_at=now_iso,
            )
            raw_record = RawBookRecord(**raw_dict)
            normalized = NormalizedBookRecord.from_raw(raw_record)
            valid_records.append(normalized)
        except (ValueError, ValidationError) as e:
            error_records.append({"url": book_url, "reason": str(e)})

    # Save to output/books.json and output/errors.json
    save_json_records("books.json", valid_records)
    if error_records:
        save_json_records("errors.json", error_records)


if __name__ == "__main__":
    main()