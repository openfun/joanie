"""
Core application admin
"""

from django.contrib import admin, messages
from django.contrib.auth import admin as auth_admin
from django.http import HttpResponseRedirect
from django.urls import re_path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from adminsortable2.admin import SortableAdminBase, SortableInlineAdminMixin
from django_object_actions import DjangoObjectActions, takes_instance_or_queryset
from parler.admin import TranslatableAdmin

from joanie.core import helpers, models
from joanie.core.enums import PRODUCT_TYPE_CERTIFICATE_ALLOWED
from joanie.core.forms import CourseRunAdminForm, ProductCourseRelationAdminForm

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


@admin.register(models.CertificateDefinition)
class CertificateDefinitionAdmin(TranslatableAdmin):
    """Admin class for the CertificateDefinition model"""

    list_display = ("name", "title")


@admin.register(models.Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """Admin class for the Certificate model"""

    list_display = ("order", "issued_on")
    readonly_fields = ("order", "issued_on", "certificate_definition")

    def certificate_definition(self, obj):  # pylint: disable=no-self-use
        """Retrieve the certification definition from the related order."""
        certificate_definition = obj.order.product.certificate_definition

        url = reverse(
            "admin:core_certificatedefinition_change",
            args=(certificate_definition.id,),
        )
        return format_html(f"<a href='{url:s}'>{certificate_definition!s}</a>")


@admin.register(models.Course)
class CourseAdmin(DjangoObjectActions, TranslatableAdmin):
    """Admin class for the Course model"""

    actions = (ACTION_NAME_GENERATE_CERTIFICATES,)
    change_actions = (ACTION_NAME_GENERATE_CERTIFICATES,)
    list_display = ("code", "title", "organization", "state")
    filter_horizontal = ("products",)
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

    form = CourseRunAdminForm
    list_display = ("title", "resource_link", "start", "end", "state", "is_gradable")
    actions = ("mark_as_gradable",)

    @admin.action(description=_("Mark course run as gradable"))
    def mark_as_gradable(self, request, queryset):  # pylint: disable=no-self-use
        """Mark selected course runs as gradable"""
        queryset.update(is_gradable=True)


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

    form = ProductCourseRelationAdminForm
    model = models.Product.target_courses.through
    extra = 0


@admin.register(models.Product)
class ProductAdmin(
    DjangoObjectActions, SortableAdminBase, TranslatableAdmin
):  # pylint: disable=too-many-ancestors
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
    actions = (ACTION_NAME_GENERATE_CERTIFICATES,)
    change_actions = (ACTION_NAME_GENERATE_CERTIFICATES,)

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

    def generate_certificates_for_course(
        self, request, product_id, course_code
    ):  # pylint: disable=no-self-use
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
                        f'<a style="margin-left: 1rem" class="button" href="{generate_certificates_url}">'  # noqa pylint: disable=line-too-long
                        f'{_("Generate certificates")}'
                        "</a>"
                    )

                raw_html += "</li>"
                items.append(raw_html)

            return format_html(f"<ul style='margin: 0'>{''.join(items)}</ul>")

        return "-"


@admin.register(models.Order)
class OrderAdmin(DjangoObjectActions, admin.ModelAdmin):
    """Admin class for the Order model"""

    list_display = ("uid", "owner", "product", "state")
    readonly_fields = ("state", "total", "proforma_invoice", "certificate")
    change_actions = (ACTION_NAME_GENERATE_CERTIFICATES,)
    actions = (ACTION_NAME_CANCEL, ACTION_NAME_GENERATE_CERTIFICATES)

    @admin.action(description=_("Cancel selected orders"))
    def cancel(self, request, queryset):  # pylint: disable=no-self-use
        """Cancel orders"""
        for order in queryset:
            order.cancel()

    @takes_instance_or_queryset
    def generate_certificates(self, request, queryset):  # pylint: disable=no-self-use
        """
        Custom action to launch generate_certificates management commands
        over the order selected
        """
        certificate_generated_count = helpers.generate_certificates_for_orders(queryset)
        summarize_certification_to_user(request, certificate_generated_count)

    def proforma_invoice(self, obj):  # pylint: disable=no-self-use
        """Retrieve the root pro forma invoice related to the order."""
        proforma_invoice = obj.proforma_invoices.get(parent__isnull=True)

        return format_html(
            (
                "<a href='"
                f"{reverse('admin:payment_proformainvoice_change', args=(proforma_invoice.id,))}"
                "'>"
                f"{str(proforma_invoice)}"
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
