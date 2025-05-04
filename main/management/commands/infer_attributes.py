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
        - "age_suitability": **Only one** of ['0-5 months', '6-11 months', '1-1.5 years', '1.6-2 years', '3-5 years', '6-8 years', '9-12 years', 'mothers', 'all ages']
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

def bucket_score(x: float) -> str:
    return (
        "very low"  if x <= 2 else
        "low"       if x <= 4 else
        "medium"    if x <= 6 else
        "high"      if x <= 8 else
        "very high"
    )


def save_embedding(self, product: Product):
    embedding_text = f"""age_suitability {product.age_suitability}; gender {product.gender}; 
    giftability {bucket_score(product.giftability)}; educational_value {bucket_score(product.educational_value)}; durability {bucket_score(product.durability)}; value_for_money {bucket_score(product.value_for_money)}; 
    safety_perception {bucket_score(product.safety_perception)}; seasonal_use {product.seasonal_use};    
    """

    embedding = client.embeddings.create(
        input=embedding_text,
        model="text-embedding-3-small",
        dimensions=1536
    )
    # print("\nGPT EMBEDDING:\n", embedding.data[0].embedding, "\n")

    try:
        embedding = np.array(embedding.data[0].embedding)
        product.embedding = embedding
        product.save()
    except Exception as e:
        self.stdout.write(self.style.ERROR(f"Error saving embedding: {e}"))
        raise 


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
        for i in range(7, number_of_products, jump):
            end = min(i + jump, number_of_products)
            self.stdout.write(f"Processing products {i+1} to {end}...")

            products = Product.objects.active().values(*fields)[i:end]
            products = list(products)

            if not products:
                self.stdout.write(self.style.WARNING("No products found — aborting."))
                return
            
            json_data = json.dumps(products, cls=DjangoJSONEncoder)
            self.stdout.write(f"JSON data: {json_data}") 

            # inferred_attributes = [
            #     {"name": "Philips Avent Natural Teat - 6M+ (2pcs)", "age_suitability": "6-11 months", "gender": "unisex", "giftability": 8, "educational_value": 2, "durability": 7, "value_for_money": 7, "safety_perception": 9, "seasonal_use": [], "sensitivity_level": 2, "waterproof": False, "portability": 9, "design_features": ["BPA-free", "anti-colic", "natural feel"], "chemical_safety": "BPA-free"},
            #     {"name": "Kinderkraft Myway Adjustable ISOFIX Car Seat - Rear to Forward Facing - Birth to 12 Years - Black", "age_suitability": "0-12 years", "gender": "unisex", "giftability": 7, "educational_value": 1, "durability": 8, "value_for_money": 6, "safety_perception": 10, "seasonal_use": [], "sensitivity_level": 3, "waterproof": True, "portability": 4, "design_features": ["adjustable headrest", "ISOFIX installation", "side protection"]},
            #     {"name": "Vicks BabyRub Oil 25ml (Moisturize, Soothe & Relax for Babies 3+ Months)", "age_suitability": "3-5 years", "gender": "unisex", "giftability": 6, "educational_value": 0, "durability": 5, "value_for_money": 8, "safety_perception": 8, "seasonal_use": [], "sensitivity_level": 1, "waterproof": False, "portability": 10},
            #     {"name": "Johnsons Bedtime Baby Shampoo - Gentle Cleansing & Soothing Care (500ml)", "age_suitability": "all ages", "gender": "unisex", "giftability": 5, "educational_value": 0, "durability": 5, "value_for_money": 6, "safety_perception": 8, "seasonal_use": [], "sensitivity_level": 1, "waterproof": True, "portability": 8, "chemical_safety": "Free from dyes, parabens, sulphates & phthalates"},
            #     {"name": "LUMALA Pixe 16\" Kids Bicycle for Girls", "age_suitability": "6-8 years", "gender": "female", "giftability": 9, "educational_value": 3, "durability": 9, "value_for_money": 7, "safety_perception": 9, "seasonal_use": [], "sensitivity_level": 2, "waterproof": False, "portability": 6, "design_features": ["sturdy training wheels", "comfortable seat", "chain guard"]},
            #     {"name": "Faber Castell School Bag M1 Watermark JK 9 Years + - red - (FC574512)", "age_suitability": "9-12 years", "gender": "unisex", "giftability": 7, "educational_value": 1, "durability": 8, "value_for_money": 7, "safety_perception": 7, "seasonal_use": [], "sensitivity_level": 2, "waterproof": True, "portability": 7, "design_features": ["lightweight", "watermark design", "cushioned straps"], "material_origin": "polyester"},
            #     {"name": "LUMALA Pixe 20\" Kids Bicycle for Girls", "age_suitability": "9-12 years", "gender": "female", "giftability": 8, "educational_value": 2, "durability": 9, "value_for_money": 7, "safety_perception": 9, "seasonal_use": [], "sensitivity_level": 3, "waterproof": False, "portability": 4, "design_features": ["sturdy construction", "front basket", "comfortable seat"]},
            #     {"name": "Philips Avent Natural Teat - 3M+ (2pcs)", "age_suitability": "3-5 years", "gender": "unisex", "giftability": 8, "educational_value": 1, "durability": 8, "value_for_money": 8, "safety_perception": 10, "seasonal_use": [], "sensitivity_level": 3, "waterproof": False, "portability": 10, "design_features": ["BPA-free", "flexible", "anti-colic"], "chemical_safety": "BPA-free"},
            #     {"name": "LUMALA Pixe 12\" Kids Bicycle for Girls", "age_suitability": "6-8 years", "gender": "female", "giftability": 8, "educational_value": 2, "durability": 8, "value_for_money": 7, "safety_perception": 9, "seasonal_use": [], "sensitivity_level": 3, "waterproof": False, "portability": 4, "design_features": ["sturdy training wheels", "comfortable seat", "front basket"]}
            # ]

            inferred_attributes = gpt_response(json_data)
            print("\nGPT OUTPUT:\n", inferred_attributes, "\n")

            # Update the product objects with the inferred attributes
            for product in inferred_attributes:
                try:
                    product_obj = Product.objects.defer("embedding").filter(name=product["name"]).first()
                    for key, value in product.items():
                        setattr(product_obj, key, value)
                    product_obj.save()
                    save_embedding(self, product_obj)
                    self.stdout.write(self.style.SUCCESS(f"Updated product: {product['name']}"))
                except Product.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Product not found: {product['name']}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error updating product {product['name']}: {e}"))
            # break

            

        

