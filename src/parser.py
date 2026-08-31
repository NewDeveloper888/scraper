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


def extract_book_details(
    html_content: str, product_url: str, source_page: str, fetched_at: str
) -> dict:
    """
    Parse a single book detail page and extract raw fields without modification.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    main_product = soup.select_one("article.product_page")
    if not main_product:
        raise ValueError(
            f"Malformed book page: could not find product article at {product_url}"
        )

    # 1. Title
    title_tag = main_product.select_one("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # 2. Price text
    price_tag = main_product.select_one("p.price_color")
    price_text = price_tag.get_text(strip=True) if price_tag else ""

    # 3. Availability text
    avail_tag = main_product.select_one("p.instock.availability")
    availability_text = avail_tag.get_text(strip=True) if avail_tag else ""

    # 4. Rating text (from class name: star-rating Three -> Three)
    rating_tag = main_product.select_one("p.star-rating")
    rating_text = ""
    if rating_tag:
        classes = rating_tag.get("class", [])
        rating_classes = [c for c in classes if c != "star-rating"]
        if rating_classes:
            rating_text = rating_classes[0]

    # 5. Description (check if product_description section exists)
    desc_header = main_product.select_one("#product_description")
    description = None
    if desc_header:
        desc_p = desc_header.find_next_sibling("p")
        if desc_p:
            description = desc_p.get_text(strip=True)

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }