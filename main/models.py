from django.db import models

# Create your models here.
class Product (models.Model):
    """
    Represents a single catalogue item imported from Kiddoz CSV.
    """

    # — core identifiers —
    url = models.URLField(unique=True)
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, blank=True)

    # — taxonomy —
    categories = models.JSONField(blank=True, null=True)          # e.g. ['Diapering', 'Bags']

    # — pricing —
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    has_discount = models.BooleanField(default=False)
    discount_percentage = models.DecimalField(max_digits=6, decimal_places=2)

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

    def __str__(self) -> str:
        return self.name