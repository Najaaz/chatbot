#!/usr/bin/env python3
"""
Improved Kiddoz.lk Product Scraper

This script scrapes product information from Kiddoz.lk product pages and saves it to a CSV file.
It extracts details such as product name, price, description, images, colors, stock status, and other available information.
"""

import requests
import csv
import os
import re
import json
import time
import random
import logging
import argparse
from datetime import datetime
from decimal import Decimal
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# import database
from main.models import Product

known_colours = [
    'black', 'white', 'blue', 'red', 'green', 'yellow', 'pink', 'purple',
    'orange', 'brown', 'grey', 'gray', 'beige', 'navy', 'maroon', 'cyan',
    'magenta', 'gold', 'silver', 'teal', 'lime', 'peach', 'cream', 'off white',
    'burgundy', 'charcoal', 'indigo', 'violet', 'lavender', 'mint', 'coral',
    'turquoise', 'khaki', 'mustard', 'plum', 'fuchsia', 'aqua', 'emerald',
    'rainbow', 'pastel', 'neon', 'electric', 'sapphire', 'ruby', 'amber',
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KiddozScraper")

class RequestHandler:
    """Handles HTTP requests with retry logic and error handling."""
    
    def __init__(self, max_retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
        """Initialize the request handler with retry settings."""
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    
    def get(self, url, timeout=15):
        """
        Perform a GET request with retry logic and error handling.
        
        Args:
            url (str): URL to request
            timeout (int): Request timeout in seconds
            
        Returns:
            requests.Response or None: Response object if successful, None otherwise
        """
        try:
            logger.info(f"Requesting URL: {url}")
            response = self.session.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"\033[91mHTTP Error: {e}\033[0m")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"\033[91mConnection Error: {e}\033[0m")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"\033[91mTimeout Error: {e}\033[0m")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"\033[91mRequest Exception: {e}\033[0m")
            return None
        except Exception as e:
            logger.error(f"\033[91mUnexpected error: {e}\033[0m")
            return None

class BaseParser:
    """Base parser for extracting common product information."""
    
    def __init__(self, soup, url):
        """Initialize the parser with BeautifulSoup object and URL."""
        self.soup = soup
        self.url = url
    
    def get_product_name(self):
        """Extract product name."""
        try:
            # Try to get from h1 tag first
            h1_elem = self.soup.select_one('h2.page-title span')
            if h1_elem and h1_elem.text.strip():
                return h1_elem.text.strip()
            
            # Fallback to title tag
            if self.soup.title:
                title_text = self.soup.title.text.strip()
                # Remove site name if present
                if ' - Kiddoz.lk' in title_text:
                    return title_text.split(' - Kiddoz.lk')[0].strip()
                return title_text
            
            return "Not found"
        except Exception as e:
            logger.error(f"\033[91mError extracting product name: {e}\033[0m")
            return "Not found"
    
    def get_brand(self):
        """Extract brand name."""
        try:
            # Try to get from brand link
            brand_elem = self.soup.select_one('#brand_link')
            if brand_elem and brand_elem.text.strip():
                return brand_elem.text.strip()
            
            # Try to get from brand info section
            brand_info = self.soup.select_one('.product-info-main .product-info-brand a')
            if brand_info and brand_info.text.strip():
                return brand_info.text.strip()
            
            # Try to get from specifications table
            specs_table = self.soup.select('.product.attribute.description table tbody tr')
            for row in specs_table:
                label = row.select_one('td:first-child')
                value = row.select_one('td:last-child')
                if label and value and 'brand' in label.text.lower():
                    return value.text.strip()
            
            # Try to get from product details
            brand_div = self.soup.select_one('.product-info-main .product-info-stock-sku .brand')
            if brand_div:
                brand_text = brand_div.text.strip()
                if ':' in brand_text:
                    return brand_text.split(':', 1)[1].strip()
                return brand_text
            
            return "Not found"
        except Exception as e:
            logger.error(f"\033[91mError extracting brand: {e}\033[0m")
            return "Not found"
    
    def get_prices(self):
        """Extract current and original prices."""
        try:
            price_data = {
                'current_price': "Not found",
                'original_price': "Not found",
                'has_discount': "No",
                'discount_percentage': 0.0
            }
            
            # Check for special price (discounted)
            special_price = self.soup.select_one('.product-info-price .special-price .price')
            old_price = self.soup.select_one('.product-info-price .old-price .price')
            
            if special_price:
                # Current price (discounted)
                price_text = special_price.text.strip()
                price_data['current_price'] = self._clean_price(price_text)
                
                # Original price
                if old_price:
                    old_price_text = old_price.text.strip()
                    price_data['original_price'] = self._clean_price(old_price_text)
                    price_data['has_discount'] = "Yes"
                    
                    # Calculate discount percentage
                    try:
                        current = float(price_data['current_price'])
                        original = float(price_data['original_price'])
                        if original > 0:
                            discount = round(((original - current) / original) * 100, 2)
                            price_data['discount_percentage'] = str(discount)
                    except (ValueError, TypeError):
                        pass
                else:
                    price_data['original_price'] = price_data['current_price']
            else:
                # Regular price (no discount)
                regular_price = self.soup.select_one('.product-info-price .price')
                if regular_price:
                    price_text = regular_price.text.strip()
                    price_data['current_price'] = self._clean_price(price_text)
                    price_data['original_price'] = price_data['current_price']
                
                # Check for discount percentage in text
                discount_elem = self.soup.select_one('.product-info-price .discount-percent')
                if discount_elem:
                    discount_text = discount_elem.text.strip()
                    discount_match = re.search(r'(-?\d+\.?\d*)%', discount_text)
                    if discount_match:
                        price_data['discount_percentage'] = discount_match.group(1)
                        price_data['has_discount'] = "Yes"
            
            return price_data
        except Exception as e:
            logger.error(f"\033[91mError extracting prices: {e}\033[0m")
            return {
                'current_price': "Not found",
                'original_price': "Not found",
                'has_discount': "No",
                'discount_percentage': "0"
            }
    
    def _clean_price(self, price_text):
        """Clean price text to extract numeric value."""
        try:
            # Remove currency symbol, commas, and other non-numeric characters
            return re.sub(r'[^\d.]', '', price_text.replace(',', ''))
        except Exception:
            return price_text
    
    def get_description(self):
        """Extract product description."""
        try:
            descriptions = []
            
            # Try to get from overview section
            desc_elem = self.soup.select('div.product.attribute.overview ul li')
            if desc_elem:
                descriptions.extend([li.text.strip() for li in desc_elem if li.text.strip()])
            
            # Try to get from basic details section
            overview_elem = self.soup.select('div.basic_details div.product.attribute p')
            if overview_elem:
                descriptions.extend([p.text.strip() for p in overview_elem if p.text.strip()])
            
            # Try to get from product highlights section
            highlights = self.soup.select('div.product-highlights ul li')
            if highlights:
                descriptions.extend([li.text.strip() for li in highlights if li.text.strip()])
            
            # Try to get from product details section
            details_elem = self.soup.select('div.product-details p')
            if details_elem:
                descriptions.extend([p.text.strip() for p in details_elem if p.text.strip()])

            # Try to get from the details overview description section
            details_desc_elem = self.soup.select('div.product.attribute.overview div.basic_details div.value')
            if not details_desc_elem:
                details_desc_elem = self.soup.select('div.product.attribute.overview div.value')
            if details_desc_elem:
                items = [desc.text.strip() for desc in details_desc_elem if desc.text.strip()]
                descriptions.extend(items)
            
            if not descriptions:
                # Try to get any text from description div
                desc_div = self.soup.select_one('div.product.attribute.description')
                if desc_div:
                    text = desc_div.get_text(strip=True)
                    if text:
                        descriptions.append(text)

            # Remove duplicates and empty strings
            descriptions = list(set(descriptions))
            return descriptions if descriptions else ["Not found"]
        except Exception as e:
            logger.error(f"\033[91mError extracting description: {e}\033[0m")
            return ["Not found"]
    
    def get_specifications(self):
        """Extract product specifications."""
        try:
            attributes = {}
            
            # Try to get from specifications table
            attr_elems = self.soup.select('.product.attribute.description table tbody tr')
            for attr in attr_elems:
                label = attr.select_one('td:first-child')
                value = attr.select_one('td:last-child')
                if label and value:
                    label_text = label.text.strip()
                    value_text = value.text.strip()
                    if label_text and value_text:
                        attributes[label_text] = value_text
            
            # Try to get from specifications section
            specs_section = self.soup.select('.specifications-of-product tr')
            for spec in specs_section:
                label = spec.select_one('td:first-child')
                value = spec.select_one('td:last-child')
                if label and value:
                    label_text = label.text.strip()
                    value_text = value.text.strip()
                    if label_text and value_text:
                        attributes[label_text] = value_text
            
            # Try to get from additional attributes section
            additional_attrs = self.soup.select('.additional-attributes-wrapper table tbody tr')
            for attr in additional_attrs:
                label = attr.select_one('th')
                value = attr.select_one('td')
                if label and value:
                    label_text = label.text.strip()
                    value_text = value.text.strip()
                    if label_text and value_text:
                        attributes[label_text] = value_text

            over_details_elem = self.soup.select('#overview_details_div div.value ul li')
            if over_details_elem:
                items = [desc.text.strip() for desc in over_details_elem if desc.text.strip()]
                for item in items:
                    # Use regex to split on :, =, -, – or —
                    split_item = re.split(r'\s*[:=–—-]\s*', item, maxsplit=1)
                    if len(split_item) == 2:
                        key, value = split_item
                        attributes[key.strip()] = value.strip()
                    else:
                        logger.warning(f"\033[93mCould not split item properly: {item}\033[0m")

            details_desc_elem = self.soup.select('div.basic_details div.value ul li')
            if details_desc_elem:
                items = [desc.text.strip() for desc in details_desc_elem if desc.text.strip()]
                for item in items:
                    # Use regex to split on :, =, -, – or —
                    split_item = re.split(r'\s*[:=–—-]\s*', item, maxsplit=1)
                    if len(split_item) == 2:
                        key, value = split_item
                        attributes[key.strip()] = value.strip()
                    else:
                        logger.warning(f"\033[93mCould not split item properly: {item}\033[0m")

            
            return attributes
        except Exception as e:
            logger.error(f"\033[91mError extracting specifications: {e}\033[0m")
            return {}
    
    def get_stock_status(self):
        """Extract stock status."""
        try:
            # Check for explicit "Out of stock" text
            stock_elem = self.soup.select_one('.stock')
            if stock_elem:
                stock_text = stock_elem.text.strip().lower()
                if 'out of stock' in stock_text:
                    return "Out of stock"
                elif 'in stock' in stock_text:
                    return "In stock"
            
            # Check for "Out of stock" text anywhere on the page
            out_of_stock_elem = self.soup.find(string=re.compile(r'Out of stock', re.I))
            if out_of_stock_elem:
                return "Out of stock"
            
            # Check for add to cart button
            add_to_cart_btn = self.soup.select_one('button.action.tocart')
            if add_to_cart_btn and 'disabled' not in add_to_cart_btn.attrs:
                return "In stock"
            
            # Check for quantity selector
            qty_input = self.soup.select_one('input.qty')
            if qty_input and 'disabled' not in qty_input.attrs:
                return "In stock"
            
            # Default to unknown if no clear indicators
            return "Unknown"
        except Exception as e:
            logger.error(f"\033[91mError extracting stock status: {e}\033[0m")
            return "Unknown"
    
    def get_color_options(self):
        """Extract color options."""
        try:
            colors = []
            color_availability = {}
            
            # Check for color swatches
            color_swatches = self.soup.select('.swatch-attribute.color .swatch-option')
            for swatch in color_swatches:
                color_name = swatch.get('data-option-label', '')
                if color_name:
                    colors.append(color_name)
                    # Check if this color is selected or available
                    is_selected = 'selected' in swatch.get('class', [])
                    is_disabled = 'disabled' in swatch.get('class', [])
                    if is_disabled:
                        color_availability[color_name] = "Out of stock"
                    else:
                        color_availability[color_name] = "In stock"
            
            # Check for color dropdown
            color_select = self.soup.select_one('select.super-attribute-select')
            if color_select:
                color_options = color_select.select('option')
                for option in color_options:
                    color_name = option.text.strip()
                    if color_name and color_name != 'Choose an Option...':
                        colors.append(color_name)
                        is_disabled = 'disabled' in option.attrs
                        if is_disabled:
                            color_availability[color_name] = "Out of stock"
                        else:
                            color_availability[color_name] = "In stock"
            
            # Check for color in product title
            product_name = self.get_product_name().lower()

            # Match all known colours in the product name (full words or phrases)
            found_colours = [c.title() for c in known_colours if c in product_name]

            if found_colours:
                colour_combination = ' & '.join(found_colours)
                if colour_combination not in colors:
                    colors.append(colour_combination)
                    color_availability[colour_combination] = self.get_stock_status()
            
            return {
                'colors': colors,
                'color_availability': color_availability
            }
        except Exception as e:
            logger.error(f"\033[91mError extracting color options: {e}\033[0m")
            return {
                'colors': [],
                'color_availability': {}
            }
    
    def get_images(self):
        """Extract product images."""
        try:
            image_urls = []
            
            # Try to get gallery data from JavaScript
            scripts = self.soup.select('script[type="text/x-magento-init"]')
            for script in scripts:
                try:
                    if not script.string:
                        continue
                    
                    data = json.loads(script.string)
                    if '[data-gallery-role=gallery-placeholder]' in data:
                        gallery_data = data['[data-gallery-role=gallery-placeholder]']['mage/gallery/gallery']
                        if 'data' in gallery_data:
                            for item in gallery_data['data']:
                                if 'full' in item:
                                    image_urls.append(item['full'])
                            break
                except (json.JSONDecodeError, KeyError):
                    continue
            
            # If no images found in gallery data, try regular image elements
            if not image_urls:
                # Try gallery placeholder images
                image_elems = self.soup.select('.gallery-placeholder img')
                for img in image_elems:
                    src = img.get('src')
                    if src:
                        # Convert relative URLs to absolute
                        abs_url = urljoin(self.url, src)
                        image_urls.append(abs_url)
                
                # Try product image photos
                if not image_urls:
                    image_elems = self.soup.select('img.product-image-photo')
                    for img in image_elems:
                        src = img.get('src')
                        if src:
                            abs_url = urljoin(self.url, src)
                            image_urls.append(abs_url)
                
                # Try data-src attributes for lazy-loaded images
                if not image_urls:
                    image_elems = self.soup.select('img[data-src]')
                    for img in image_elems:
                        src = img.get('data-src')
                        if src:
                            abs_url = urljoin(self.url, src)
                            image_urls.append(abs_url)

            # Get images in the general product image section
            image_elems = self.soup.select('div.basic_details div.value figure img')
            for img in image_elems:
                src = img.get('src')
                if src and src not in image_urls:
                    abs_url = urljoin(self.url, src)
                    image_urls.append(abs_url)
            
            return {
                'image_urls': image_urls,
                'image_count': len(image_urls)
            }
        except Exception as e:
            logger.error(f"\033[91mError extracting images: {e}\033[0m")
            return {
                'image_urls': [],
                'image_count': 0
            }
    
    def get_categories(self):
        """Extract product categories from breadcrumbs."""
        try:
            breadcrumbs = self.soup.select('.breadcrumbs .items li')
            categories = []
            
            for crumb in breadcrumbs[1:-1]:  # Skip first (Home) and last (Product) items
                # Get category text
                category_text = crumb.text.strip()
                if category_text:
                    categories.append(category_text)
            
            return categories if categories else "Not found"
        except Exception as e:
            logger.error(f"\033[91mError extracting categories: {e}\033[0m")
            return "Not found"
    
    def get_ratings(self):
        """Extract product ratings and review count."""
        try:
            rating_data = {
                'rating': "Not found",
                'review_count': "0"
            }
            
            # Try to get rating percentage
            rating_elem = self.soup.select_one('.star_avg_tr1.star_avg_td1')
            if rating_elem:
                rating_text = rating_elem.text.strip()
                rating_match = re.search(r'(\d+)%', rating_text)
                if rating_match:
                    # Convert percentage to 5-star scale
                    rating_percent = int(rating_match.group(1))
                    rating_data['rating'] = str(round((rating_percent / 100) * 5, 1))
            
            # Try to get rating from stars
            if rating_data['rating'] == "Not found":
                rating_elem = self.soup.select_one('.rating-result')
                if rating_elem:
                    rating_width = rating_elem.get('style', '')
                    width_match = re.search(r'width:\s*(\d+)%', rating_width)
                    if width_match:
                        rating_percent = int(width_match.group(1))
                        rating_data['rating'] = str(round((rating_percent / 100) * 5, 1))
            
            # Try to get review count
            reviews_count_elem = self.soup.select_one('.reviews-actions .action.view')
            if reviews_count_elem:
                reviews_text = reviews_count_elem.text.strip()
                reviews_match = re.search(r'(\d+)', reviews_text)
                if reviews_match:
                    rating_data['review_count'] = reviews_match.group(1)
            
            # Try alternative review count location
            if rating_data['review_count'] == "0":
                reviews_count_elem = self.soup.select_one('.product-reviews-summary .reviews-actions')
                if reviews_count_elem:
                    reviews_text = reviews_count_elem.text.strip()
                    reviews_match = re.search(r'(\d+)', reviews_text)
                    if reviews_match:
                        rating_data['review_count'] = reviews_match.group(1)
            
            return rating_data
        except Exception as e:
            logger.error(f"\033[91mError extracting ratings: {e}\033[0m")
            return {
                'rating': "Not found",
                'review_count': "0"
            }
    
    def get_sku(self):
        """Extract product SKU."""
        try:
            # Try to get from SKU element
            sku_elem = self.soup.select_one('.product.attribute.sku .value')
            if sku_elem:
                return sku_elem.text.strip()
            
            # Try to get from product info stock sku
            sku_div = self.soup.select_one('.product-info-stock-sku .sku')
            if sku_div:
                sku_text = sku_div.text.strip()
                if ':' in sku_text:
                    return sku_text.split(':', 1)[1].strip()
                return sku_text
            
            # Try to get from URL
            url_match = re.search(r'k-(\d+)\.html$', self.url)
            if url_match:
                return url_match.group(1)
            
            return "Not found"
        except Exception as e:
            logger.error(f"\033[91mError extracting SKU: {e}\033[0m")
            return "Not found"
    
    def parse(self):
        """Parse all product information."""
        product_data = {
            'url': self.url,
            'scrape_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'name': self.get_product_name(),
            'brand': self.get_brand(),
            'sku': self.get_sku(),
            'categories': self.get_categories(),
        }
        
        # Get prices
        price_data = self.get_prices()
        product_data.update(price_data)
        
        # Get stock status
        product_data['availability'] = self.get_stock_status()
        
        # Get color options
        color_data = self.get_color_options()
        product_data['color_options'] = json.dumps(color_data['colors'])
        product_data['color_availability'] = json.dumps(color_data['color_availability'])
        
        # Get description
        product_data['description'] = json.dumps(self.get_description())
        
        # Get specifications
        product_data['specifications'] = json.dumps(self.get_specifications())
        
        # Get images
        image_data = self.get_images()
        product_data['image_urls'] = json.dumps(image_data['image_urls'])
        product_data['image_count'] = image_data['image_count']
        
        # Get ratings
        rating_data = self.get_ratings()
        product_data.update(rating_data)
        
        return product_data

class ClothingParser(BaseParser):
    """Parser specialized for clothing products."""
    
    def get_color_options(self):
        """Extract color options for clothing products."""
        try:
            # Get base color options
            base_colors = super().get_color_options()
            
            # Additional clothing-specific color extraction
            color_labels = self.soup.select('.product-options-wrapper .swatch-attribute-label')
            for label in color_labels:
                if 'color' in label.text.lower():
                    color_options = label.find_next('div', class_='swatch-attribute-options')
                    if color_options:
                        swatches = color_options.select('.swatch-option')
                        for swatch in swatches:
                            color_name = swatch.get('option-label', '')
                            if color_name and color_name not in base_colors['colors']:
                                base_colors['colors'].append(color_name)
                                # Check if this color is selected or available
                                is_disabled = 'disabled' in swatch.get('class', [])
                                if is_disabled:
                                    base_colors['color_availability'][color_name] = "Out of stock"
                                else:
                                    base_colors['color_availability'][color_name] = "In stock"
            
            return base_colors
        except Exception as e:
            logger.error(f"\033[91mError extracting clothing color options: {e}\033[0m")
            return super().get_color_options()
    
    def get_size_options(self):
        """Extract size options for clothing products."""
        try:
            sizes = []
            size_availability = {}
            
            # Check for size swatches
            size_swatches = self.soup.select('.swatch-attribute.size .swatch-option')
            for swatch in size_swatches:
                size_name = swatch.get('option-label', '')
                if size_name:
                    sizes.append(size_name)
                    # Check if this size is selected or available
                    is_disabled = 'disabled' in swatch.get('class', [])
                    if is_disabled:
                        size_availability[size_name] = "Out of stock"
                    else:
                        size_availability[size_name] = "In stock"
            
            # Check for size dropdown
            size_select = self.soup.select_one('select.super-attribute-select')
            if size_select:
                size_options = size_select.select('option')
                for option in size_options:
                    size_name = option.text.strip()
                    if size_name and size_name != 'Choose an Option...':
                        sizes.append(size_name)
                        is_disabled = 'disabled' in option.attrs
                        if is_disabled:
                            size_availability[size_name] = "Out of stock"
                        else:
                            size_availability[size_name] = "In stock"
            
            return {
                'sizes': sizes,
                'size_availability': size_availability
            }
        except Exception as e:
            logger.error(f"\033[91mError extracting size options: {e}\033[0m")
            return {
                'sizes': [],
                'size_availability': {}
            }
    
    def parse(self):
        """Parse clothing product information."""
        # Get base product data
        product_data = super().parse()
        
        # Add clothing-specific data
        try:
            # Get size options
            size_data = self.get_size_options()
            product_data['size_options'] = json.dumps(size_data['sizes'])
            product_data['size_availability'] = json.dumps(size_data['size_availability'])
            
            # Extract age group if available
            product_name = product_data['name']
            age_match = re.search(r'(\d+[-\s]?\d*)\s*(years|months|yrs|mos)', product_name, re.IGNORECASE)
            if age_match:
                product_data['age_group'] = age_match.group(0)
            else:
                product_data['age_group'] = "Not specified"
            
            # Extract gender if available
            if re.search(r'\b(boys|boy|men|man)\b', product_name, re.IGNORECASE):
                product_data['gender'] = "male"
            elif re.search(r'\b(girls|girl|women|woman)\b', product_name, re.IGNORECASE):
                product_data['gender'] = "female"
            else:
                product_data['gender'] = "unisex"
            
        except Exception as e:
            logger.error(f"\033[91mError parsing clothing-specific data: {e}\033[0m")
        
        return product_data

class ToysParser(BaseParser):
    """Parser specialized for toy products."""
    
    def get_age_recommendation(self):
        """Extract age recommendation for toys."""
        try:
            age_recommendation = "Not specified"
            
            # Check product name
            product_name = self.get_product_name()
            age_match = re.search(r'(\d+[-\s]?\d*)\s*(years|months|yrs|mos|\+)', product_name, re.IGNORECASE)
            if age_match:
                age_recommendation = age_match.group(0)
            
            # Check product description
            if age_recommendation == "Not specified":
                description = self.get_description()
                for desc in description:
                    age_match = re.search(r'(\d+[-\s]?\d*)\s*(years|months|yrs|mos|\+)', desc, re.IGNORECASE)
                    if age_match:
                        age_recommendation = age_match.group(0)
                        break
            
            # Check specifications
            if age_recommendation == "Not specified":
                specs = self.get_specifications()
                for key, value in specs.items():
                    if 'age' in key.lower():
                        age_recommendation = value
                        break
            
            return age_recommendation
        except Exception as e:
            logger.error(f"\033[91mError extracting age recommendation: {e}\033[0m")
            return "Not specified"
    
    def parse(self):
        """Parse toy product information."""
        # Get base product data
        product_data = super().parse()
        
        # Add toy-specific data
        try:
            # Get age recommendation
            product_data['age_recommendation'] = self.get_age_recommendation()
            
            # Extract material information if available
            specs = json.loads(product_data['specifications'])
            material = "Not specified"
            for key, value in specs.items():
                if 'material' in key.lower():
                    material = value
                    break
            
            product_data['material'] = material
            
        except Exception as e:
            logger.error(f"\033[91mError parsing toy-specific data: {e}\033[0m")
        
        return product_data

class DiaperParser(BaseParser):
    """Parser specialized for diaper products."""
    
    def get_size_info(self):
        """Extract size information for diapers."""
        try:
            size_info = {
                'size': "Not specified",
                'weight_range': "Not specified",
                'count': "Not specified"
            }
            
            # Check product name for size
            product_name = self.get_product_name()
            
            # Extract size
            size_match = re.search(r'\b(newborn|new born|nb|small|medium|large|xl|xxl|s|m|l)\b', 
                                  product_name, re.IGNORECASE)
            if size_match:
                size_info['size'] = size_match.group(0).upper()
            
            # Extract count
            count_match = re.search(r'(\d+)\s*(pcs|pieces|pack|count)', product_name, re.IGNORECASE)
            if count_match:
                size_info['count'] = count_match.group(1)
            
            # Extract weight range
            weight_match = re.search(r'(\d+[-\s]?\d*)\s*kg', product_name, re.IGNORECASE)
            if weight_match:
                size_info['weight_range'] = weight_match.group(0)
            
            # Check specifications for more detailed information
            specs = self.get_specifications()
            for key, value in specs.items():
                key_lower = key.lower()
                if 'size' in key_lower and size_info['size'] == "Not specified":
                    size_info['size'] = value
                elif 'weight' in key_lower and size_info['weight_range'] == "Not specified":
                    size_info['weight_range'] = value
                elif ('count' in key_lower or 'pieces' in key_lower) and size_info['count'] == "Not specified":
                    if value.isdigit():
                        size_info['count'] = value
            
            return size_info
        except Exception as e:
            logger.error(f"\033[91mError extracting diaper size info: {e}\033[0m")
            return {
                'size': "Not specified",
                'weight_range': "Not specified",
                'count': "Not specified"
            }
    
    def parse(self):
        """Parse diaper product information."""
        # Get base product data
        product_data = super().parse()
        
        # Add diaper-specific data
        try:
            # Get size information
            size_info = self.get_size_info()
            product_data.update(size_info)
            
        except Exception as e:
            logger.error(f"\033[91mError parsing diaper-specific data: {e}\033[0m")
        
        return product_data

class ProductParser:
    """Factory for creating appropriate parser based on product type."""
    
    @staticmethod
    def create_parser(soup, url):
        """Create appropriate parser based on product category."""
        try:
            # Extract categories from breadcrumbs
            breadcrumbs = soup.select('.breadcrumbs .items li a')
            categories = [crumb.text.strip().lower() for crumb in breadcrumbs if crumb.text.strip()]
            
            # Determine product type based on categories
            if any(cat in ['clothing', 'baby clothing', 'kids clothing', 'boys clothing', 'girls clothing'] 
                  for cat in categories):
                return ClothingParser(soup, url)
            elif any(cat in ['toys', 'toys & gaming', 'soft toys', 'educational games'] 
                    for cat in categories):
                return ToysParser(soup, url)
            elif any(cat in ['diapering', 'diapers', 'wet wipes'] 
                    for cat in categories):
                return DiaperParser(soup, url)
            else:
                return BaseParser(soup, url)
        except Exception as e:
            logger.error(f"\033[91mError creating parser: {e}\033[0m")
            return BaseParser(soup, url)

class DataProcessor:
    """Processes and standardizes extracted data."""
    
    @staticmethod
    def process_product_data(product_data):
        """Process and standardize product data."""
        try:
            # Ensure all required fields are present
            required_fields = [
                'url', 'scrape_date', 'name', 'brand', 'current_price', 
                'original_price', 'has_discount', 'description', 'availability',
                'image_urls', 'image_count'
            ]
            
            for field in required_fields:
                if field not in product_data:
                    product_data[field] = "Not found"
            
            # Convert JSON strings to actual JSON for display
            json_fields = ['description', 'specifications', 'image_urls', 
                          'color_options', 'color_availability']
            
            for field in json_fields:
                if field in product_data and isinstance(product_data[field], str):
                    try:
                        # Validate JSON
                        json.loads(product_data[field])
                    except json.JSONDecodeError:
                        # If not valid JSON, make it valid
                        product_data[field] = json.dumps([product_data[field]])
            
            return product_data
        except Exception as e:
            logger.error(f"\033[91mError processing product data: {e}\033[0m")
            return product_data

class StorageManager:
    """Handles saving data to CSV and other formats."""
    
    def __init__(self, filename='kiddoz_products.csv'):
        """Initialize the storage manager with filename."""
        self.filename = filename
        self.fieldnames = None  # Will store column headers
    
    def save_to_db(self, product_data):
        """Save product data to the database file."""
        try:
            # URL is ignored since the unique constraint is on the name field
            product, created = Product.objects.update_or_create(
            name=product_data['name'],
            defaults={
                'brand': product_data.get('brand', ''),
                'categories': product_data.get('categories', []),

                'current_price': Decimal(str(product_data.get('current_price', 0))),
                'original_price': Decimal(str(product_data.get('original_price', 0))),
                'has_discount': str(product_data.get('has_discount', '')).lower() == 'yes',
                'discount_percentage': Decimal(str(product_data.get('discount_percentage', 0))),

                'in_stock': str(product_data.get('availability', '')).lower() == 'in stock',
                'color_options': json.loads(product_data.get('color_options', '[]')),
                'color_availability': json.loads(product_data.get('color_availability', '{}')),

                'description': json.loads(product_data.get('description', '[]')),
                'specifications': json.loads(product_data.get('specifications', '{}')),

                'image_urls': json.loads(product_data.get('image_urls', '[]')),
                'image_count': int(product_data.get('image_count', 0)),

                'rating': Decimal(str(product_data['rating'])) if product_data.get('rating') not in [None, 'Not found'] else None,
                'size': product_data.get('size', ''),
                'weight_range': product_data.get('weight_range', ''),
                'count': int(product_data['count']) if product_data.get('count') not in [None, 'Not specified', 'Not found'] else None,
                'is_active': True,
                }
            )

            logger.info(f"{'Created' if created else 'Updated'} product in DB: {product.name}")
            return True
    
        except Exception as e:
            logger.error(f"\033[91mError saving product to database: {e}\033[0m")
            raise e
    
class KiddozScraper:
    """Main scraper class that orchestrates the scraping process."""
    
    def __init__(self, max_retries=3, delay=1.0, timeout=30, use_selenium=False):
        """Initialize the scraper with settings."""
        self.request_handler = RequestHandler(max_retries=max_retries)
        self.storage_manager = StorageManager()
        self.delay = delay
        self.timeout = timeout
        self.failed_urls = []
        self.use_selenium = use_selenium
        Product.objects.update(is_active=False)  # Mark all products as inactive before scraping
    
    def scrape_product(self, url):
        """Scrape a single product page."""
        try:
            print("\n" + "="*50 + "\n")
            logger.info(f"Scraping product: {url}")
            
            ################# BS4 CODE #################

            if self.use_selenium:
                # Load the page with Selenium
                options = webdriver.ChromeOptions()
                # options.add_argument('--headless')  # Comment this out if you want to see the browser
                options.add_argument('--disable-gpu')
                options.add_argument('--no-sandbox')

                try:
                    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                    driver.set_page_load_timeout(self.timeout)
                    driver.get(url)

                    # Wait for a specific element that indicates the page is fully loaded
                    try:
                        WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".swatch-attribute.color"))
                        )
                    except TimeoutException:
                        logger.warning(f"\033[93mTimeout waiting for content on: {url}\033[0m")

                    html = driver.page_source
                    soup = BeautifulSoup(html, 'html.parser')
                    driver.quit()
                except WebDriverException as e:
                    logger.error(f"\033[91mSelenium WebDriver Error: {e}\033[0m")
                    self.failed_urls.append(url)
                    return None
            else:
                 # Get page content
                response = self.request_handler.get(url, timeout=self.timeout)
                if not response:
                    logger.error(f"\033[91mFailed to get response from {url}\033[0m")
                    self.failed_urls.append(url)
                    return None
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
            
            # Create appropriate parser
            parser = ProductParser.create_parser(soup, url)
            
            # Parse product data
            product_data = parser.parse()
            
            # Process and standardize data
            product_data = DataProcessor.process_product_data(product_data)
            
            logger.info(f"Successfully scraped: {product_data['name']}")
            return product_data
        except Exception as e:
            logger.error(f"\033[91mError scraping product {url}: {e}\033[0m")
            self.failed_urls.append(url)
            return None
    
    def scrape_products(self, urls, output_file='kiddoz_products.csv', max_workers=5):
        """Scrape multiple product pages."""
        try:
            # Set output file
            self.storage_manager.filename = output_file
            
            # Remove existing file if it exists
            if os.path.exists(output_file):
                os.remove(output_file)
                logger.info(f"Removed existing file: {output_file}")
            
            # Reset failed URLs
            self.failed_urls = []
            
            # Scrape products
            successful_count = 0
            total_count = len(urls)
            
            logger.info(f"Starting to scrape {total_count} products")
            
            # Use ThreadPoolExecutor for parallel scraping
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {executor.submit(self.scrape_product, url): url for url in urls}
                
                for i, future in enumerate(future_to_url):
                    url = future_to_url[future]
                    try:
                        product_data = future.result()
                        
                        # Save product data
                        if product_data:
                            self.storage_manager.save_to_db(product_data)
                            successful_count += 1
                        
                        # Log progress
                        logger.info(f"Progress: {i+1}/{total_count} ({successful_count} successful, {len(self.failed_urls)} failed)")
                        
                        # Add delay between submissions to avoid overloading
                        time.sleep(self.delay / max_workers)
                    except Exception as e:
                        logger.error(f"\033[91mError processing result for {url}: {e}\033[0m")
                        self.failed_urls.append(url)
            
            # Log summary
            logger.info(f"Scraping completed: {successful_count}/{total_count} products scraped successfully")
            
            return successful_count, self.failed_urls, len(self.failed_urls)
        except Exception as e:
            logger.error(f"\033[91mError in scrape_products: {e}\033[0m")
            return 0, len(urls)

