from fetcher import fetch_page

def main():
    target_url = "https://books.toscrape.com/catalogue/page-1.html"
    print("Testing Stage 1...")
    fetch_page(target_url, custom_cache_name="catalogue-page-1")

if __name__ == "__main__":
    main()