from django.contrib import admin

from .models import Pricing, Product, ProductPrice, ProductPriceRange, ProductPricePackLine


class ProductPriceRangeInline(admin.TabularInline):
    model = ProductPriceRange
    extra = 0


class ProductPricePackLineInline(admin.TabularInline):
    model = ProductPricePackLine
    extra = 0


class ProductPriceAdmin(admin.ModelAdmin):
    inlines = [ProductPriceRangeInline, ProductPricePackLineInline]
    list_display = ('pricing', 'product', 'year')
    search_fields = ('pricing__name', 'product__name', 'year')


class PricingAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')
    


admin.site.register(Pricing, PricingAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductPrice, ProductPriceAdmin)
admin.site.register(ProductPriceRange)
admin.site.register(ProductPricePackLine)
