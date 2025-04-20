import requests
from bs4 import BeautifulSoup
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


def webscrape_all_products(url) -> list[str]:
    try:
        # Send a GET request to the URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all <li> elements with class "product"
        product_items = soup.find_all('li', class_='product')

        # Extract links from these products
        product_links = []
        for product in product_items:
            # Find the first <a> tag within the product
            link = product.find('a')
            if link and 'href' in link.attrs:
                product_links.append(link['href'])

        return product_links

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

class Command(BaseCommand):
    """
    Usage: python manage.py webscrape_all_products
    """

    help = "Scrapes kiddoz.lk product links from the sitemap and stores them as a txt file."

    def handle(self, *args, **options):
        target_url = "https://kiddoz.lk/sitemap"
        self.stdout.write(f"Scraping {target_url} …")

        links = webscrape_all_products(target_url)
        if not links:
            self.stdout.write(self.style.WARNING("No links found — aborting."))
            return

        # Write to MEDIA_ROOT/scraped/product_links_YYYYMMDD.txt
        today = timezone.now().strftime("%Y%m%d")
        output_dir = Path(settings.MEDIA_ROOT) / "scraped"
        output_dir.mkdir(parents=True, exist_ok=True)

        outfile = output_dir / f"product_links.txt"
        outfile.write_text("\n".join(links), encoding="utf-8")

        self.stdout.write(
           f"Saved {len(links)} links → {outfile.relative_to(Path.cwd())}"
        )