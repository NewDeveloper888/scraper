from datetime import datetime, timezone
import time
from pydantic import ValidationError
from fetcher import fetch_page
from models import NormalizedBookRecord, RawBookRecord
from parser import extract_book_details, extract_book_links, extract_next_page_url
from storage import save_json_records, save_run_report


def discover_books(
    start_url: str, max_pages: int = 3
) -> tuple[list[tuple[str, str]], int, int, int]:
    current_url = start_url
    pages_crawled = 0
    discovered: list[tuple[str, str]] = []
    cache_hits = 0
    network_fetches = 0

    while current_url and pages_crawled < max_pages:
        pages_crawled += 1
        cache_name = f"catalogue-page-{pages_crawled}"

        html_content, from_cache = fetch_page(
            current_url, custom_cache_name=cache_name
        )
        if from_cache:
            cache_hits += 1
        else:
            network_fetches += 1

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

    return unique_items, pages_crawled, cache_hits, network_fetches


def main(inject_fake_url: bool = True):
    start_time_iso = datetime.now(timezone.utc).isoformat()
    start_clock = time.perf_counter()

    print("Stage 5: Surviving failures and generating run report...")

    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    (
        book_entries,
        cat_pages,
        total_cache_hits,
        total_network_fetches,
    ) = discover_books(start_url, max_pages=3)

    # Injected fake URL to prove fault tolerance without hammering the host
    if inject_fake_url:
        book_entries.append(
            (
                "https://books.toscrape.com/catalogue/deliberately-broken-fake-book_0000/index.html",
                start_url,
            )
        )

    valid_records: list[NormalizedBookRecord] = []
    error_records: list[dict] = []
    failed_pages_count = 0

    for book_url, source_page in book_entries:
        html_content, from_cache = fetch_page(book_url)

        if from_cache:
            total_cache_hits += 1
        else:
            total_network_fetches += 1

        if not html_content:
            failed_pages_count += 1
            error_records.append(
                {"url": book_url, "reason": "Failed to fetch page HTML"}
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
            failed_pages_count += 1
            error_records.append({"url": book_url, "reason": str(e)})

    # Persist data
    save_json_records("books.json", valid_records)
    if error_records:
        save_json_records("errors.json", error_records)

    duration = round(time.perf_counter() - start_clock, 3)

    report = {
        "start_time": start_time_iso,
        "duration_seconds": duration,
        "catalogue_pages_crawled": cat_pages,
        "detail_pages_total": len(book_entries),
        "cache_hits": total_cache_hits,
        "network_fetches": total_network_fetches,
        "valid_records": len(valid_records),
        "invalid_records": len(error_records),
        "failed_pages": failed_pages_count,
    }

    save_run_report(report)


if __name__ == "__main__":
    main(inject_fake_url=True)