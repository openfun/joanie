"""Badges application admin"""

from django.contrib import admin

from parler.admin import TranslatableAdmin

from joanie.badges import models


@admin.register(models.Badge)
class BadgeAdmin(TranslatableAdmin):
    """Admin class for the Badge model"""

    list_display = ("name", "description", "iri", "provider")
    list_filter = ("provider",)


@admin.register(models.IssuedBadge)
class IssuedBadgeAdmin(TranslatableAdmin):
    """Admin class for the IssuedBadge model"""

    list_display = ("badge", "user")
    list_filter = (
        "badge",
        "badge__provider",
    )
    search_fields = (
        "id",
        "user__username",
        "user__email",
        "badge__id",
        "badge__translations__name",
        "badge__iri",
    )
