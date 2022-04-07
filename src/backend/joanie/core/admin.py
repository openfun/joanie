"""
Core application admin
"""
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin
from parler.admin import TranslatableAdmin

from . import models


@admin.register(models.CertificateDefinition)
class CertificateDefinitionAdmin(TranslatableAdmin):
    """Admin class for the CertificateDefinition model"""

    list_display = ("name", "title")


@admin.register(models.Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """Admin class for the Certificate model"""

    list_display = ("order", "issued_on")


@admin.register(models.Course)
class CourseAdmin(TranslatableAdmin):
    """Admin class for the Course model"""

    list_display = ("code", "title", "organization", "state")
    filter_vertical = ("products",)
    fieldsets = (
        (_("Main information"), {"fields": ("code", "title", "organization")}),
        (
            _("Related products"),
            {
                "description": _(
                    "Select products that will be available through this course."
                ),
                "fields": ("products",),
            },
        ),
    )


@admin.register(models.CourseRun)
class CourseRunAdmin(TranslatableAdmin):
    """Admin class for the CourseRun model"""

    list_display = ("title", "resource_link", "start", "end", "state")


@admin.register(models.Organization)
class OrganizationAdmin(TranslatableAdmin):
    """Admin class for the Organization model"""

    list_display = ("code", "title")


@admin.register(models.User)
class UserAdmin(auth_admin.UserAdmin):
    """Admin class for the User model"""

    list_display = ("username",)


class ProductCourseRelationInline(SortableInlineAdminMixin, admin.TabularInline):
    """Admin class for the ProductCourseRelation model"""

    model = models.Product.target_courses.through
    extra = 0


@admin.register(models.Product)
class ProductAdmin(SortableAdminMixin, TranslatableAdmin):
    """Admin class for the Product model"""

    list_display = ("title", "type", "price")
    fields = (
        "type",
        "title",
        "description",
        "call_to_action",
        "price",
        "certificate_definition",
        "related_courses",
    )

    inlines = (ProductCourseRelationInline,)
    readonly_fields = ("related_courses",)

    @admin.display(description="Related courses")
    def related_courses(self, obj):  # pylint: disable=no-self-use
        """
        Retrieve courses related to the product
        """
        related_courses = obj.courses.all()
        if related_courses:
            items = [
                (
                    "<li>"
                    f"<a href='{reverse('admin:core_course_change', args=(course.id,),)}'>"
                    f"{course.code} | {course.title}"
                    "</a>"
                    "</li>"
                )
                for course in obj.courses.all()
            ]
            return format_html(f"<ul style='margin: 0'>{''.join(items)}</ul>")
        return "-"


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin class for the Order model"""

    list_display = ("uid", "owner", "product", "state")
    readonly_fields = ("total", "invoice")
    actions = ["cancel"]

    @admin.action(description=_("Cancel selected orders"))
    def cancel(self, request, queryset):  # pylint: disable=no-self-use
        """Cancel orders"""
        for order in queryset:
            order.cancel()

    def invoice(self, obj):  # pylint: disable=no-self-use
        """Retrieve the root invoice related to the order."""
        invoice = obj.invoices.get(parent__isnull=True)

        return format_html(
            (
                f"<a href='{reverse('admin:payment_invoice_change', args=(invoice.id,), )}'>"
                f"{str(invoice)}"
                "</a>"
            )
        )


@admin.register(models.Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """Admin class for the Enrollment model"""

    list_display = ("user", "order", "course_run", "state")


@admin.register(models.Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin class for the Address model"""

    list_display = (
        "title",
        "full_name",
        "address",
        "postcode",
        "city",
        "country",
        "is_main",
        "owner",
    )
