from django.db import models
from django.utils import timezone

class Sale(models.Model):
    date = models.DateField(default=timezone.now)
    price_sold = models.DecimalField(max_digits=10, decimal_places=2)
    price_purchased = models.DecimalField(max_digits=10, decimal_places=2)
    product_name = models.CharField(max_length=200)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.product_name} - {self.date}"
    
    @property
    def profit(self):
        return self.price_sold - self.price_purchased