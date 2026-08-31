from urllib.parse import urljoin
from bs4 import BeautifulSoup


def extract_book_links(html_content: str, base_url: str) -> list[str]:
    """
    Extract product detail page links from a single catalogue page.
    Convert relative links to absolute URLs safely.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    book_links: list[str] = []

    # Target the article cards for books
    articles = soup.select("article.product_pod")
    for article in articles:
        link_tag = article.select_one("h3 a")
        if link_tag and link_tag.get("href"):
            relative_href = link_tag["href"]
            # Convert relative URL to an absolute URL
            absolute_url = urljoin(base_url, relative_href)
            book_links.append(absolute_url)

    return book_links


def extract_next_page_url(html_content: str, base_url: str) -> str | None:
    """
    Locate the 'next' pagination button and return its absolute URL.
    Returns None if there is no next page.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    next_tag = soup.select_one("li.next a")
    if next_tag and next_tag.get("href"):
        return urljoin(base_url, next_tag["href"])
    return None