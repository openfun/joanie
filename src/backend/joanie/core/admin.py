"""
Core application admin
"""
from django.contrib import admin
from django.contrib.auth import admin as auth_admin

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

    list_display = ("title", "organization")


@admin.register(models.CourseRun)
class CourseRunAdmin(TranslatableAdmin):
    """Admin class for the CourseRun model"""

    list_display = ("title", "resource_link", "start", "end")


@admin.register(models.Organization)
class OrganizationAdmin(TranslatableAdmin):
    """Admin class for the Organization model"""

    list_display = ("code", "title")


@admin.register(models.User)
class UserAdmin(auth_admin.UserAdmin):
    """Admin class for the User model"""

    list_display = ("username",)


@admin.register(models.Product)
class ProductAdmin(TranslatableAdmin):
    """Admin class for the Product model"""

    list_display = ("title", "type", "price")


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin class for the Order model"""

    list_display = ("owner", "product", "state")


@admin.register(models.ProductCourseRelation)
class ProductCourseRelationAdmin(admin.ModelAdmin):
    """Admin class for the ProductCourseRelation model"""

    list_display = ("product", "course", "position")


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
