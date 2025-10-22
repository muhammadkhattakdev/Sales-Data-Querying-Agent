from django.contrib import admin
from .models import Sale

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'date', 'price_purchased', 'price_sold', 'profit']
    list_filter = ['date', 'product_name']
    search_fields = ['product_name']
    date_hierarchy = 'date'
    
    def profit(self, obj):
        return f"${obj.profit:.2f}"
    profit.short_description = 'Profit'

