from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import time
from main.management.commands.kiddoz_scraper import KiddozScraper  # <-- assuming all scraping classes are in kiddoz_scraper.py

import logging

logger = logging.getLogger("KiddozScraper")

LIMIT = 4  # Set to 0 for no limit, or specify a number to limit the number of products scraped
WORKERS = 4  # Number of threads to use for scraping
USE_SELENIUM = True  # Set to True if you want to use Selenium for JS-rendered pages


class Command(BaseCommand):
    help = "Scrapes product data from Kiddoz.lk and saves to CSV (nightly run)"

    def handle(self, *args, **options):
        input_file = Path(settings.MEDIA_ROOT) / "scraped" / "product_links.txt"
        output_file = Path(settings.MEDIA_ROOT) / "scraped" / "kiddoz_products.csv"
        failed_file = Path(settings.MEDIA_ROOT) / "failed" / f"failed_urls_{time.strftime('%Y%m%d')}.txt"

        # Ensure output dir exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if not input_file.exists():
            self.stdout.write(self.style.ERROR(f"❌ File not found: {input_file}"))
            return

        # Read URLs
        with open(input_file, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
        
        # Apply limit if specified
        if LIMIT > 0:
            urls = urls[:LIMIT]

        # Initialise the scraper
        scraper = KiddozScraper(
            max_retries=3,
            delay=1.0,
            timeout=30,
            use_selenium=USE_SELENIUM  # Set True if you want JS-rendered support
        )

        # Scrape products
        success_count, failed_urls, failed_count = scraper.scrape_products(
            urls=urls,
            output_file=str(output_file),
            max_workers=WORKERS  # Adjust based on your CPU cores
        )

        # Write failed URLs to a file
        if failed_urls:
            with open(failed_file, "w") as f:
                for url in failed_urls:
                    f.write(f"{url}\n")
            self.stdout.write(self.style.WARNING(f"⚠️ Failed URLs saved to: {failed_file}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Scraped {success_count} products"))
        if failed_count:
            self.stdout.write(self.style.WARNING(f"⚠️ {failed_count} products failed. See 'failed_urls.txt'"))
