from fetcher import fetch_page
from parser import extract_book_links, extract_next_page_url


def discover_books(start_url: str, max_pages: int = 3) -> list[str]:
    """
    Crawl through catalogue pages up to max_pages and collect all unique book URLs.
    """
    current_url = start_url
    pages_crawled = 0
    discovered_urls: list[str] = []

    while current_url and pages_crawled < max_pages:
        pages_crawled += 1
        cache_name = f"catalogue-page-{pages_crawled}"

        html_content, _ = fetch_page(current_url, custom_cache_name=cache_name)
        if not html_content:
            print(f"[ERROR] Could not load catalogue page: {current_url}")
            break

        # Extract book links from the current page
        links = extract_book_links(html_content, base_url=current_url)
        discovered_urls.extend(links)

        # Find the next page link if we haven't reached the limit yet
        if pages_crawled < max_pages:
            current_url = extract_next_page_url(html_content, base_url=current_url)
        else:
            current_url = None

    # Deduplicate while preserving order
    unique_urls = list(dict.fromkeys(discovered_urls))

    print(
        f"catalogue_pages={pages_crawled}, discovered={len(discovered_urls)}, unique_urls={len(unique_urls)}"
    )
    return unique_urls


def main():
    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    print("Running Stage 2...")
    books = discover_books(start_url, max_pages=3)


if __name__ == "__main__":
    main()