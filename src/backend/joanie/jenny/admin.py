from django.contrib import admin

from .models import Pricing, Product, ProductPrice, ProductPriceRange, ProductPricePackLine, Transaction, Quote, Invoice, CourseSubmission, Contract, InvoiceLine, QuoteLine, CourseSubmissionProduct

class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceLineInline]


class QuoteLineInline(admin.TabularInline):
    model = QuoteLine
    extra = 0

class CourseSubmissionProductInline(admin.TabularInline):
    model = CourseSubmissionProduct
    extra = 0

class QuoteAdmin(admin.ModelAdmin):
    inlines = [QuoteLineInline]

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
    
class CourseSubmissionAdmin(admin.ModelAdmin):
    inlines=[CourseSubmissionProductInline]


admin.site.register(Pricing, PricingAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductPrice, ProductPriceAdmin)
admin.site.register(ProductPriceRange)
admin.site.register(ProductPricePackLine)
admin.site.register(Transaction)
admin.site.register(Contract)
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(Quote, QuoteAdmin)
admin.site.register(CourseSubmission, CourseSubmissionAdmin)
