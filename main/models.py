from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from pgvector.django import VectorField


age_suitability_choices = (
    ('0-5 months', '0-5 months'),
    ('6-11 months', '6-11 months'),
    ('1-1.5 years', '1-1.5 years'),
    ('1.6-2 years', '1.6-2 years'),
    ('3-5 years', '3-5 years'),
    ('6-8 years', '6-8 years'),
    ('9-12 years', '9-12 years'),
    ('mothers', 'mothers'),
    ('all ages', 'all ages'),
)

gender_choices = (
    ('male', 'male'),
    ('female', 'female'),
    ('unisex', 'unisex'),
)

months = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

class ProductManager(models.Manager):

    def active(self):
        return self.get_queryset().filter(is_active=True)

# Create your models here.
class Product (models.Model):
    """
    Represents a single catalogue item imported from Kiddoz CSV.
    """

    # — core identifiers —
    url = models.URLField(unique=True)
    name = models.CharField(max_length=255, unique=True)
    brand = models.CharField(max_length=255, blank=True)

    # — taxonomy —
    categories = models.JSONField(blank=True, null=True)          # e.g. ['Diapering', 'Bags']

    # — pricing —
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    has_discount = models.BooleanField(default=False)
    discount_percentage = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])

    # — stock & variant info —
    in_stock = models.BooleanField(default=True)                # e.g. “In stock” / “Out of stock”
    color_options = models.JSONField(blank=True, null=True)       # e.g. ["Beige", "Pink"]
    color_availability = models.JSONField(blank=True, null=True)  # e.g. {"Beige": "Out of stock"}

    # — product copy —
    description = models.JSONField(blank=True)                    # long‑form marketing copy
    specifications = models.JSONField(blank=True, null=True)      # key‑value tech specs

    # — media —
    image_urls = models.JSONField(blank=True, null=True)          # list of image URLs
    image_count = models.PositiveIntegerField(default=0)

    # — extra attributes —
    rating = models.DecimalField(max_digits=3, decimal_places=2,
                                 blank=True, null=True)           # e.g. 4.75
    size = models.CharField(max_length=50, blank=True)            # free‑text (“LARGE” etc.)
    weight_range = models.CharField(max_length=50, blank=True)    # free‑text (“0‑6 kg” etc.)
    count = models.PositiveIntegerField(blank=True, null=True)    # quantity pack‑size etc.

    # — housekeeping —
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)                # soft delete flag

    # — inferred attributes —
    age_suitability = models.CharField(max_length=20, choices=age_suitability_choices, default='0-5 months')  # e.g. "0-5 months"
    gender = models.CharField(max_length=10, choices=gender_choices, default='unisex')  # e.g. "Unisex"
    giftability = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(10)])  # e.g. 8.5
    educational_value = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(10)])  # e.g. 7.5
    durability = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(10)])  # e.g. 9.0
    value_for_money = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(10)])  # e.g. 8.0
    safety_perception = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(10)])  # e.g. 9.5
    seasonal_use = models.JSONField(default=list, blank=True) # e.g. [1,4,5] (1=Jan, 2=Feb, ... 12=Dec)

    # — LLM inferred attributes —
    sensitivity_level = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(10)])  # e.g. 5.0
    waterproof = models.BooleanField(default=False)  # e.g. True/False
    portability = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(10)])  # e.g. 6.0
    design_features = models.JSONField(blank=True, null=True)  # e.g. ["Ergonomic", "Compact"]
    package_quantity = models.PositiveIntegerField(default=1)  # e.g. 10 (number of items in a package)
    usage_type = models.CharField(max_length=50, blank=True)  # e.g. "Everyday Use", "Occasional Use"
    material_origin = models.CharField(max_length=50, blank=True)  # e.g. "Organic Cotton", "Synthetic"
    chemical_safety = models.CharField(max_length=50, blank=True)  # e.g. "Non-toxic", "Treated"

    embedding = VectorField(dimensions=1536, null=True, blank=True)  # e.g. (vector representation of the product)  


    objects = ProductManager()

    def __str__(self) -> str:
        return self.name
    
    def get_seasonal_month_names(self):
        """
        Returns a list of month names based on the seasonal_use field.
        """
        return [months[month] for month in self.seasonal_use if month in months]
    
    def clean(self):
        """
        Custom validation logic for the Product model.
        """
        # Validate that the discount percentage is between 0 and 100 if has_discount is True
        if self.has_discount and (self.discount_percentage <= 0 or self.discount_percentage >= 100):
            raise ValidationError("Discount percentage must be between 0 and 100 when has_discount is True.")
        elif not self.has_discount:
            self.discount_percentage = 0.0

        # Validate that the seasonal_use field contains valid month numbers (1-12) in a list
        if not isinstance(self.seasonal_use, list):
            raise ValidationError("seasonal_use must be a list of months.")
        if not all(isinstance(m, int) and 1 <= m <= 12 for m in self.seasonal_use):
            raise ValidationError("Each month in seasonal_use must be an integer between 1 and 12.")
        
        if self.age_suitability:
            self.age_suitability = self.age_suitability.replace("–", "-").strip()
        
    def save(self, *args, **kwargs):
        self.full_clean()  # Run all model validation
        super().save(*args, **kwargs)
