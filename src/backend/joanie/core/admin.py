"""
Core application admin
"""

from django.contrib import admin, messages
from django.contrib.admin.options import csrf_protect_m
from django.contrib.auth import admin as auth_admin
from django.contrib.sites.models import Site
from django.http import HttpResponseRedirect
from django.urls import re_path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from admin_auto_filters.filters import AutocompleteFilter
from adminsortable2.admin import SortableAdminBase, SortableInlineAdminMixin
from django_object_actions import DjangoObjectActions, takes_instance_or_queryset
from parler.admin import TranslatableAdmin, TranslatableStackedInline

from joanie.core import forms, helpers, models
from joanie.core.enums import PRODUCT_TYPE_CERTIFICATE_ALLOWED

ACTION_NAME_GENERATE_CERTIFICATES = "generate_certificates"
ACTION_NAME_CANCEL = "cancel"


def summarize_certification_to_user(request, count):
    """
    Display a message after generate_certificates command has been launched
    """
    if count == 0:
        messages.warning(
            request,
            _("No certificates have been generated."),
        )
    else:
        messages.success(
            request,
            ngettext_lazy(  # pylint: disable=no-member
                "{:d} certificate has been generated.",
                "{:d} certificates have been generated.",
                count,
            ).format(count),
        )


# Admin filters


class RequiredFilterMixin:
    """Make filter required ie don't show any results until it has a value."""

    def queryset(self, request, queryset):
        """Don't return any results until a value is selected in the filter."""
        if self.value():
            return super().queryset(request, queryset)

        return super().queryset(request, queryset).none()


class CourseFilter(AutocompleteFilter):
    """Filter on a "course" foreign key."""

    title = _("Course")
    field_name = "course"


class ProductFilter(AutocompleteFilter):
    """Filter on a "product" foreign key."""

    title = _("Product")
    field_name = "product"


class OrganizationFilter(AutocompleteFilter):
    """Filter on an "organization" foreign key."""

    title = _("Organization")
    field_name = "organization"


class RequiredOrganizationFilter(RequiredFilterMixin, AutocompleteFilter):
    """Required Filter on an "organization" foreign key."""

    title = _("Organization")
    field_name = "organization"


class OwnerFilter(AutocompleteFilter):
    """Filter on an "owner" foreign key."""

    title = _("Owner")
    field_name = "owner"


class RequiredUserFilter(RequiredFilterMixin, AutocompleteFilter):
    """Required filter on an "user" foreign key."""

    title = _("User")
    field_name = "user"


class CourseRunFilter(AutocompleteFilter):
    """Filter on a "course_run" foreign key."""

    title = _("Course run")
    field_name = "course_run"


# Admin registers


@admin.register(models.ContractDefinition)
class ContractDefinitionAdmin(admin.ModelAdmin):
    """Admin class for the ContractDefinition model"""

    list_display = ("title", "language")


@admin.register(models.Contract)
class ContractAdmin(admin.ModelAdmin):
    """Admin class for the Contract model"""

    list_display = (
        "order",
        "owner",
        "organization",
        "student_signed_on",
        "signature_backend_reference",
    )
    readonly_fields = (
        "definition",
        "definition_checksum",
        "student_signed_on",
        "order",
        "organization",
        "organization_signatory",
        "organization_signed_on",
        "owner",
        "signature_backend_reference",
    )

    def owner(self, obj):  # pylint: disable=no-self-use
        """Retrieve the owner of the contract from the related order."""
        return obj.order.owner

    def organization(self, obj):  # pylint: disable=no-self-use
        """Retrieve the organization of the contract from the related order."""
        return obj.order.organization


@admin.register(models.CertificateDefinition)
class CertificateDefinitionAdmin(TranslatableAdmin):
    """Admin class for the CertificateDefinition model"""

    list_display = ("name", "title")
    search_fields = ("name", "translations__title")


@admin.register(models.Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """Admin class for the Certificate model"""

    list_display = ("organization", "order", "enrollment", "owner", "issued_on")
    list_filter = [RequiredOrganizationFilter]
    search_fields = [
        "order__owner__username__iexact",
        "order__owner__first_name__icontains",
        "order__owner__email__iexact",
        "enrollment__user__username__iexact",
        "enrollment__user__first_name__icontains",
        "enrollment__user__email__iexact",
    ]
    readonly_fields = (
        "id",
        "organization",
        "order",
        "enrollment",
        "issued_on",
        "owner",
        "certificate_definition",
    )

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        """
        Add instruction to explain that, due to the RequiredOrganizationFilter, no results will be
        shown until the view is filtered for a specific organization.
        """
        extra_context = extra_context or {}
        extra_context["subtitle"] = _(
            "To get results, choose an organization on the right first, "
            "then type the username of the student in the search bar."
        )
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(models.OrderGroup)
class OrderGroupAdmin(admin.ModelAdmin):
    """Admin class for the OrderGroup model"""

    list_display = (
        "course_product_relation",
        "is_active",
        "is_enabled",
        "nb_available_seats",
        "start",
        "end",
        "discount",
    )
    search_fields = ("course_product_relation", "start", "end")
    fields = (
        "course_product_relation",
        "is_enabled",
        "is_active",
        "nb_seats",
        "start",
        "end",
        "discount",
    )
    readonly_fields = ("nb_available_seats", "is_enabled")
    readonly_update_fields = ("course_product_relation", "nb_seats")

    def get_readonly_fields(self, request, obj=None):
        """
        Make some fields readonly on update to avoid changing them by mistake
        """
        if obj is None:
            return self.readonly_fields

        return self.readonly_fields + self.readonly_update_fields

    def nb_available_seats(self, obj):  # pylint: disable=no-self-use
        """Return the number of available seats for this order group."""
        return obj.available_seats


class CourseProductRelationInline(admin.StackedInline):
    """Admin class for the CourseProductRelation model"""

    form = forms.CourseProductRelationAdminForm
    model = models.Course.products.through
    extra = 0
    autocomplete_fields = ["product"]


class CourseCourseRunsInline(admin.TabularInline):
    """Admin class for the CourseCourseRunsInline"""

    model = models.CourseRun
    show_change_link = True

    readonly_fields = (
        "title",
        "resource_link",
        "enrollment_start",
        "enrollment_end",
        "start",
        "end",
        "is_listed",
        "is_gradable",
    )
    fields = (
        "title",
        "resource_link",
        "enrollment_start",
        "enrollment_end",
        "start",
        "end",
        "is_listed",
        "is_gradable",
    )
    extra = 0


@admin.register(models.Course)
class CourseAdmin(DjangoObjectActions, TranslatableAdmin):
    """Admin class for the Course model"""

    actions = (ACTION_NAME_GENERATE_CERTIFICATES,)
    autocomplete_fields = ["organizations"]
    change_actions = (ACTION_NAME_GENERATE_CERTIFICATES,)
    change_form_template = "joanie/admin/translatable_change_form_with_actions.html"
    list_display = ("code", "title", "state")
    readonly_fields = ("course_runs",)
    filter_horizontal = ("products",)
    inlines = (CourseCourseRunsInline, CourseProductRelationInline)
    fieldsets = (
        (
            _("Main information"),
            {
                "fields": (
                    "code",
                    "title",
                    "cover",
                    "effort",
                )
            },
        ),
        (
            _("Organizations"),
            {
                "description": _("Select organizations that author this course."),
                "fields": ("organizations",),
            },
        ),
    )
    search_fields = ["code", "translations__title"]

    @takes_instance_or_queryset
    def generate_certificates(self, request, queryset):  # pylint: disable no-self-use
        """
        Custom action to generate certificates for a collection of courses
        passed as a queryset
        """
        certificate_generated_count = helpers.generate_certificates_for_orders(
            models.Order.objects.filter(course__in=queryset)
        )

        summarize_certification_to_user(request, certificate_generated_count)


@admin.register(models.CourseRun)
class CourseRunAdmin(TranslatableAdmin):
    """Admin class for the CourseRun model"""

    actions = ("mark_as_gradable",)
    autocomplete_fields = ["course"]
    fieldsets = (
        (
            _("Main information"),
            {
                "fields": (
                    "id",
                    "course",
                    "title",
                    "resource_link",
                    "is_gradable",
                    "is_listed",
                    "languages",
                    "enrollment_start",
                    "enrollment_end",
                    "start",
                    "end",
                )
            },
        ),
    )
    list_display = (
        "title",
        "resource_link",
        "start",
        "end",
        "state",
        "is_gradable",
        "is_listed",
    )
    list_filter = [CourseFilter, "is_gradable", "is_listed"]
    readonly_fields = ("id",)
    search_fields = [
        "resource_link",
        "translations__title",
        "course__code",
        "course__translations__title",
    ]

    @admin.action(description=_("Mark course run as gradable"))
    def mark_as_gradable(self, request, queryset):  # pylint: disable=no-self-use
        """Mark selected course runs as gradable"""
        queryset.update(is_gradable=True)


@admin.register(models.Organization)
class OrganizationAdmin(TranslatableAdmin):
    """Admin class for the Organization model"""

    list_display = ("code", "title")
    search_fields = ["code", "translations__title"]


@admin.register(models.User)
class UserAdmin(auth_admin.UserAdmin):
    """Admin class for the User model"""

    list_display = (
        "username",
        "get_full_name",
        "email",
        "language",
    )
    fieldsets = (
        (None, {"fields": ("username", "first_name", "last_name", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "email",
                    "language",
                    "has_subscribed_to_commercial_newsletter",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ("language",)
    readonly_update_fields = ("username",)

    def get_readonly_fields(self, request, obj=None):
        """
        Make some fields readonly on update to avoid changing them by mistake
        """
        if obj is None:
            return self.readonly_fields

        return self.readonly_fields + self.readonly_update_fields


class ProductTargetCourseRelationInline(SortableInlineAdminMixin, admin.TabularInline):
    """Admin class for the ProductTargetCourseRelation model"""

    autocomplete_fields = ["course"]
    form = forms.ProductTargetCourseRelationAdminForm
    model = models.Product.target_courses.through
    extra = 0


@admin.register(models.Product)
class ProductAdmin(
    DjangoObjectActions,
    SortableAdminBase,
    TranslatableAdmin,
):  # pylint: disable=too-many-ancestors
    """Admin class for the Product model"""

    change_form_template = "joanie/admin/translatable_change_form_with_actions.html"
    list_display = ("title", "type", "price")
    fieldsets = (
        (
            _("Main information"),
            {
                "fields": (
                    "id",
                    "type",
                    "title",
                    "description",
                    "instructions",
                    "call_to_action",
                    "price",
                    "contract_definition",
                    "related_courses",
                )
            },
        ),
        (
            _("Certifications"),
            {
                "fields": (
                    "certificate_definition",
                    "certification_level",
                    "teachers",
                    "skills",
                )
            },
        ),
    )
    inlines = (ProductTargetCourseRelationInline,)
    list_filter = ["type"]
    readonly_fields = (
        "id",
        "related_courses",
    )
    actions = (ACTION_NAME_GENERATE_CERTIFICATES,)
    change_actions = (ACTION_NAME_GENERATE_CERTIFICATES,)
    search_fields = ["translations__title"]

    def get_change_actions(self, request, object_id, form_url):
        """
        Remove the generate_certificates action from list of actions
        if the product instance is not certifying
        """
        actions = super().get_change_actions(request, object_id, form_url)
        actions = list(actions)

        if not self.model.objects.filter(
            pk=object_id, type__in=PRODUCT_TYPE_CERTIFICATE_ALLOWED
        ).exists():
            actions.remove(ACTION_NAME_GENERATE_CERTIFICATES)

        return actions

    def get_urls(self):
        """
        Add url to trigger certificate generation for a course - product couple.
        """
        url_patterns = super().get_urls()

        return [
            re_path(
                r"^(?P<product_id>.+)/generate-certificates/(?P<course_code>.+)/$",
                self.admin_site.admin_view(self.generate_certificates_for_course),
                name=ACTION_NAME_GENERATE_CERTIFICATES,
            )
        ] + url_patterns

    @takes_instance_or_queryset
    def generate_certificates(self, request, queryset):  # pylint: disable=no-self-use
        """
        Custom action to generate certificates for a collection of products
        passed as a queryset
        """
        certificate_generated_count = helpers.generate_certificates_for_orders(
            models.Order.objects.filter(product__in=queryset)
        )

        summarize_certification_to_user(request, certificate_generated_count)

    def generate_certificates_for_course(self, request, product_id, course_code):  # pylint: disable=no-self-use
        """
        A custom action to generate certificates for a course - product couple.
        """
        certificate_generated_count = helpers.generate_certificates_for_orders(
            models.Order.objects.filter(
                product__id=product_id, course__code=course_code
            )
        )

        summarize_certification_to_user(request, certificate_generated_count)

        return HttpResponseRedirect(
            reverse("admin:core_product_change", args=(product_id,))
        )

    @admin.display(description="Related courses")
    def related_courses(self, obj):  # pylint: disable=no-self-use
        """
        Retrieve courses related to the product
        """
        return self.get_related_courses_as_html(obj)

    @staticmethod
    def get_related_courses_as_html(obj):  # pylint: disable=no-self-use
        """
        Get the html representation of the product's related courses
        """
        related_courses = obj.courses.all()
        is_certifying = obj.type in PRODUCT_TYPE_CERTIFICATE_ALLOWED

        if related_courses:
            items = []
            for course in obj.courses.all():
                change_course_url = reverse(
                    "admin:core_course_change",
                    args=(course.id,),
                )

                raw_html = (
                    '<li style="margin-bottom: 1rem">'
                    f"<a href='{change_course_url}'>{course.code} | {course.title}</a>"
                )

                if is_certifying:
                    # Add a button to generate certificate
                    generate_certificates_url = reverse(
                        f"admin:{ACTION_NAME_GENERATE_CERTIFICATES}",
                        kwargs={"product_id": obj.id, "course_code": course.code},
                    )

                    raw_html += (
                        f'<a style="margin-left: 1rem" class="button" href="{generate_certificates_url}">'  # pylint: disable=line-too-long
                        f"{_('Generate certificates')}"
                        "</a>"
                    )

                raw_html += "</li>"
                items.append(raw_html)

            return format_html(f"<ul style='margin: 0'>{''.join(items)}</ul>")

        return "-"


@admin.register(models.Discount)
class DiscountAdmin(admin.ModelAdmin):
    """Admin class for the Discount model"""

    list_display = ("id", "string_discount_value", "is_used")
    search_fields = ["rate", "amount"]
    readonly_fields = ("is_used",)

    def is_used(self, obj):  # pylint: disable=no-self-use
        """Returns a counter of how many times the discount is used in order groups"""
        return obj.usage_count

    @admin.display(description="Discount")
    def string_discount_value(self, obj):  # pylint: disable=no-self-use
        """Returns the string representation of the discount value."""
        return str(obj)


@admin.register(models.Order)
class OrderAdmin(DjangoObjectActions, admin.ModelAdmin):
    """Admin class for the Order model"""

    actions = (ACTION_NAME_CANCEL, ACTION_NAME_GENERATE_CERTIFICATES)
    autocomplete_fields = ["course", "enrollment", "organization", "owner", "product"]
    change_actions = (ACTION_NAME_GENERATE_CERTIFICATES,)
    list_display = ("id", "created_on", "organization", "owner", "product", "state")
    list_filter = [OwnerFilter, OrganizationFilter, ProductFilter, "state"]
    readonly_fields = (
        "state",
        "total",
        "has_waived_withdrawal_right",
        "invoice",
        "certificate",
    )
    search_fields = ["course__translations__title", "organization__translations__title"]

    @admin.action(description=_("Cancel selected orders"))
    def cancel(self, request, queryset):  # pylint: disable=no-self-use
        """Cancel orders"""
        for order in queryset:
            order.flow.cancel()

    @takes_instance_or_queryset
    def generate_certificates(self, request, queryset):  # pylint: disable=no-self-use
        """
        Custom action to launch generate_certificates management commands
        over the order selected
        """
        certificate_generated_count = helpers.generate_certificates_for_orders(queryset)
        summarize_certification_to_user(request, certificate_generated_count)

    def invoice(self, obj):  # pylint: disable=no-self-use
        """Retrieve the root invoice related to the order."""
        invoice = obj.invoices.get(parent__isnull=True)

        return format_html(
            (
                "<a href='"
                f"{reverse('admin:payment_invoice_change', args=(invoice.id,))}"
                "'>"
                f"{str(invoice)}"
                "</a>"
            )
        )


@admin.register(models.Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """Admin class for the Enrollment model"""

    autocomplete_fields = ["course_run", "user"]
    list_display = ("user", "course_run", "state")
    list_filter = [RequiredUserFilter, CourseRunFilter, "state"]
    list_select_related = ("user", "course_run")
    search_fields = (
        "user__email",
        "user__username",
        "course_run__course__organizations__translations__title",
        "course_run__course__translations__title",
    )

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        """
        Add instruction to explain that, due to the RequiredUserFilter, no results will be
        shown until the view is filtered for a specific user.
        """
        extra_context = extra_context or {}
        extra_context["subtitle"] = _("To get results, choose a user on the right")
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(models.Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin class for the Address model"""

    autocomplete_fields = ["owner", "organization"]
    list_display = (
        "title",
        "full_name",
        "address",
        "postcode",
        "city",
        "country",
        "is_main",
        "owner",
        "organization",
    )
    list_filter = [OwnerFilter, OrganizationFilter, "is_main"]
    list_select_related = ["owner", "organization"]
    search_fields = ["title", "first_name", "last_name", "address", "postcode", "city"]

    @csrf_protect_m
    def get_queryset(self, request):
        """
        Returns an empty queryset of Addresses because we want the user to apply a filter to get
        some results (either an owner or an organization).
        """
        queryset = super().get_queryset(request)
        if not request.GET:
            return models.Address.objects.none()
        return queryset

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        """
        Add instructions to explain that, due to the `OrganizationFilter` and
        `OwnerFilter`, no result will be shown until the view is filtered for a specific
        'organization' or 'owner'.
        """
        extra_context = extra_context or {}
        extra_context["subtitle"] = _(
            "To get results, choose an owner or an organization on the right"
        )
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(models.CourseWish)
class CourseWishAdmin(admin.ModelAdmin):
    """Admin class for the CourseWish model"""

    list_display = (
        "course",
        "owner",
    )
    list_filter = [CourseFilter, OwnerFilter]
    readonly_fields = ("id",)
    search_fields = [
        "owner__last_name",
        "owner__username",
        "owner__email",
        "course__code",
        "course__translations__title",
    ]


@admin.register(models.Teacher)
class TeacherAdmin(admin.ModelAdmin):
    """Admin class for the Teacher model"""

    list_display = ("first_name", "last_name")
    search_fields = ["first_name", "last_name"]


@admin.register(models.Skill)
class SkillAdmin(TranslatableAdmin):
    """Admin class for the Skill model"""

    list_display = ("title",)
    search_fields = ["translations__title"]


class SiteConfigInline(TranslatableStackedInline):
    """Inline for sites with config fields."""

    model = models.SiteConfig
    can_delete = False
    verbose_name = _("Config field")
    verbose_name_plural = _("Config fields")


class SiteAdmin(admin.ModelAdmin):
    """Admin class for the SiteConfig model."""

    list_display = ("name", "domain")
    search_fields = ("name", "domain")
    inlines = [
        SiteConfigInline,
    ]


# Unregister the original Site admin
admin.site.unregister(Site)
admin.site.register(Site, SiteAdmin)
