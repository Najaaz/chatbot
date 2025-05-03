import os, json
import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from main.models import Product
from openai import OpenAI

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """
        You are a world-class algorithm that extracts structured information for product recommendation purposes in an e-commerce setting focused on children's and parenting products.

        From the input product information — including fields such as name, brand, categories, description, specifications, images, etc. — extract and return only the following attributes using structured reasoning. Your output must be a raw JSON array, with each product represented as a JSON object using the name as its unique identifier.

        For each product, infer the following:
        - "name": Product's name (string). Must be present.
        - "age_suitability": One of ['0-5 months', '6-11 months', '1-1.5 years', '1.6-2 years', '3-5 years', '6-8 years', '9-12 years', 'mothers', 'all ages']
        - "gender": One of ['male', 'female', 'unisex']
        - "giftability": Integer from 0-10
        - "educational_value": Integer from 0-10
        - "durability": Integer from 0-10
        - "value_for_money": Integer from 0-10
        - "safety_perception": Integer from 0-10
        - "seasonal_use": List of integers (1-12) representing months, or empty list if not seasonal
        - "sensitivity_level": Integer from 0-10
        - "waterproof": Boolean (true or false)
        - "portability": Integer from 0-10
        - "design_features": List of strings (e.g., ["compact", "colorful", "ergonomic"])
        - "package_quantity": Positive integer if known; omit field if unknown
        - "usage_type": Short description string if known (e.g., "feeding accessory"); omit if unknown
        - "material_origin": String (e.g., "organic cotton", "synthetic") if known; omit if unknown
        - "chemical_safety": String (e.g., "BPA-free", "non-toxic") if known; omit if unknown

        ✅ Rules:
            - Always include the "name" field.
            - Only output raw JSON — do not use Markdown formatting or code blocks.
            - If any value is unknown or not inferable, omit the key.
            - Return a JSON array with several product objects, one per product.
            - Keep the output concise to Python's structured JSON format.
            - Ensure all output uses plain ASCII characters. **Do not use Unicode** punctuation
    """
}

# Initialize OpenAI API client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))   


def gpt_response(prompt: str) -> object:
    """
    Uses the OpenAI API to get a response for the given prompt.
    """
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[SYSTEM_MESSAGE, {"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=2048,
    )
    raw = response.choices[0].message
    print("\nGPT OUTPUT:\n", raw, "\n")

    try:
        content = json.loads(raw.content)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

    return content


class Command(BaseCommand):
    """
    Usage: python manage.py infer_attributes
    """

    help = "Uses the OpenAI API to infer attributes for all products in the database."

    def handle(self, *args, **options):
        self.stdout.write("Starting attribute inference for all products...")

        # Only choose the first 20 columns of the products table
        fields = [field.name for field in Product._meta.fields if field.name not in ['image_urls', 'id', 'url']][:17]
        number_of_products = Product.objects.active().count()

        self.stdout.write(f"Number of products to process: {number_of_products}")
        self.stdout.write(f"Fields to process: {fields}\n")

        jump = 7
        for i in range(0, number_of_products, jump):
            end = min(i + jump, number_of_products)
            self.stdout.write(f"Processing products {i+1} to {end}...")

            products = Product.objects.active().values(*fields)[i:end]
            products = list(products)

            if not products:
                self.stdout.write(self.style.WARNING("No products found — aborting."))
                return
            
            json_data = json.dumps(products, cls=DjangoJSONEncoder)
            self.stdout.write(f"JSON data: {json_data}") 

            # inferred_attributes =  []
            inferred_attributes = gpt_response(json_data)
            print("\nGPT OUTPUT:\n", inferred_attributes, "\n")

            # Update the product objects with the inferred attributes
            for product in inferred_attributes:
                try:
                    product_obj = Product.objects.defer("embedding").filter(name=product["name"]).first()
                    for key, value in product.items():
                        setattr(product_obj, key, value)
                    product_obj.save()
                    self.stdout.write(self.style.SUCCESS(f"Updated product: {product['name']}"))
                except Product.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Product not found: {product['name']}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error updating product: {e}"))
            # break

            

        

