# ruff: noqa: SLF001
# pylint: disable=too-many-lines
"""Admin serializers for Joanie Core app."""

import csv
from decimal import Decimal as D

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from django_countries.serializer_fields import CountryField
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from joanie.core import enums, models
from joanie.core.serializers.fields import (
    ImageDetailField,
    ISO8601DurationField,
    ThumbnailDetailField,
)
from joanie.core.utils import Echo, get_default_currency_symbol
from joanie.core.utils.batch_order import get_active_offering_rule
from joanie.core.utils.organization import get_least_active_organization
from joanie.payment import models as payment_models


class AdminContractDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for ContractDefinition model."""

    title = serializers.CharField()
    name = serializers.ChoiceField(
        required=False,
        choices=models.ContractDefinition._meta.get_field("name").choices,
        default=models.ContractDefinition._meta.get_field("name").default,
        label=models.ContractDefinition._meta.get_field("name").verbose_name,
    )

    class Meta:
        model = models.ContractDefinition
        fields = ("id", "body", "appendix", "description", "language", "title", "name")
        read_only_fields = ["id"]


class AdminCertificateDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for CertificationDefinition model."""

    title = serializers.CharField()
    description = serializers.CharField(required=False)

    class Meta:
        model = models.CertificateDefinition
        fields = ("id", "name", "title", "description", "template")
        read_only_fields = ["id"]


class AdminQuoteDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for QuoteDefinition model."""

    title = serializers.CharField()
    name = serializers.ChoiceField(
        choices=models.QuoteDefinition._meta.get_field("name").choices,
    )
    description = serializers.CharField(required=False)

    class Meta:
        model = models.QuoteDefinition
        fields = ("id", "title", "description", "name", "body", "language")
        read_only_fields = ["id"]


class AdminCourseLightSerializer(serializers.ModelSerializer):
    """Read-only light serializer for Course model."""

    class Meta:
        model = models.Course
        fields = ("code", "title", "id", "state")
        read_only_fields = ("code", "title", "id", "state")


class AdminCourseRunLightSerializer(serializers.ModelSerializer):
    """Serializer for CourseRun model."""

    title = serializers.CharField()
    languages = serializers.MultipleChoiceField(
        choices=models.CourseRun._meta.get_field("languages").choices
    )
    is_gradable = serializers.BooleanField(
        required=False,
        # default=False,
        # label=_("Is gradable")
        default=models.CourseRun._meta.get_field("is_gradable").default,
        label=models.CourseRun._meta.get_field("is_gradable").verbose_name,
    )
    is_listed = serializers.BooleanField(
        required=False,
        default=models.CourseRun._meta.get_field("is_listed").default,
        label=models.CourseRun._meta.get_field("is_listed").verbose_name,
        help_text=models.CourseRun._meta.get_field("is_listed").help_text,
    )

    class Meta:
        model = models.CourseRun
        fields = [
            "id",
            "resource_link",
            "title",
            "is_gradable",
            "is_listed",
            "languages",
            "start",
            "end",
            "enrollment_start",
            "enrollment_end",
            "uri",
            "state",
        ]
        read_only_fields = ["id", "uri", "state"]


class AdminUserSerializer(serializers.ModelSerializer):
    """Read only serializer for User model."""

    full_name = serializers.CharField(source="get_full_name")

    class Meta:
        model = models.User
        fields = ["id", "username", "full_name", "email"]
        read_only_fields = fields


class AdminUserCompleteSerializer(serializers.ModelSerializer):
    """Serializer for User model with additional data."""

    full_name = serializers.CharField(source="get_full_name")
    abilities = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.User
        fields = [
            "id",
            "username",
            "full_name",
            "is_superuser",
            "is_staff",
            "abilities",
            "email",
        ]
        read_only_fields = fields

    def get_abilities(self, user):
        """Return abilities of the logged-in user on itself."""
        request = self.context.get("request")
        if request:
            return request.user.get_abilities(user)
        return {}


class AdminOrganizationLightSerializer(serializers.ModelSerializer):
    """Read-only light Serializer for Organization model."""

    class Meta:
        model = models.Organization
        fields = ("code", "title", "id")
        read_only_fields = ("code", "title", "id")


class AdminOrganizationAccessSerializer(serializers.ModelSerializer):
    """Serializer for OrganizationAccess model."""

    user = AdminUserSerializer(read_only=True)
    role = serializers.ChoiceField(
        required=False,
        choices=models.OrganizationAccess._meta.get_field("role").choices,
        default=models.OrganizationAccess._meta.get_field("role").default,
    )

    class Meta:
        model = models.OrganizationAccess
        fields = (
            "id",
            "user",
            "role",
        )
        read_only_fields = (
            "id",
            "user",
        )

    def validate(self, attrs):
        """
        Validate that the organization access has at least a user id
        and an organization id provided.
        """
        validated_data = super().validate(attrs)

        # Retrieve organization instance from context and add it to validated_data
        organization_id = self.context.get("organization_id")
        validated_data["organization"] = get_object_or_404(
            models.Organization, id=organization_id
        )

        # Retrieve user instance from context and add it to validated_data
        user_id = self.initial_data.get("user_id")
        if user_id is not None:
            try:
                validated_data["user"] = models.User.objects.get(id=user_id)
            except models.User.DoesNotExist as exception:
                raise serializers.ValidationError(
                    {"user_id": "Resource does not exist."}
                ) from exception
        elif self.partial is False and user_id is None:
            raise serializers.ValidationError({"user_id": "This field is required."})

        return validated_data


class AdminOrganizationAddressSerializer(serializers.ModelSerializer):
    """Serializer for the Address model for an organization"""

    is_main = serializers.BooleanField(
        required=False,
        default=models.Address._meta.get_field("is_main").default,
        label=models.Address._meta.get_field("is_main").verbose_name,
    )
    is_reusable = serializers.BooleanField(
        required=False,
        default=models.Address._meta.get_field("is_reusable").default,
        label=models.Address._meta.get_field("is_reusable").verbose_name,
    )

    class Meta:
        model = models.Address
        fields = [
            "id",
            "title",
            "address",
            "postcode",
            "city",
            "country",
            "first_name",
            "last_name",
            "is_main",
            "is_reusable",
        ]
        read_only_fields = [
            "id",
        ]

    def create(self, validated_data):
        """
        Create a new address and attach it to the provided organization.
        """
        validation_error = {}
        organization_id = self.context.get("organization_id", None)

        if organization_id is None:
            validation_error["organization_id"] = "This field is required"

        if validation_error:
            raise serializers.ValidationError(validation_error)

        try:
            organization = models.Organization.objects.get(pk=organization_id)
        except models.Organization.DoesNotExist as exception:
            raise serializers.ValidationError(
                {"organization_id": "Resource does not exist."}
            ) from exception

        validated_data["organization"] = organization

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Update the address object if the offering exists between the address and the
        provided organization.
        """
        if organization_id := self.context.get("organization_id", None):
            try:
                models.Address.objects.get(
                    pk=instance.pk, organization_id=organization_id
                )
            except models.Address.DoesNotExist as exception:
                raise serializers.ValidationError(
                    {
                        "detail": (
                            "The offering does not exist between the address and the organization."
                        )
                    }
                ) from exception

        if organization_id is None:
            raise serializers.ValidationError(
                {"organization_id": "This field is required."}
            )

        return super().update(instance, validated_data)


class AdminOrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model."""

    title = serializers.CharField()
    logo = ThumbnailDetailField(required=False)
    signature = ImageDetailField(required=False)
    accesses = AdminOrganizationAccessSerializer(many=True, read_only=True)
    addresses = AdminOrganizationAddressSerializer(many=True, read_only=True)
    country = serializers.ChoiceField(
        required=False,
        choices=models.Organization._meta.get_field("country").choices,
        default=models.Organization._meta.get_field("country").default,
        help_text=models.Organization._meta.get_field("country").help_text,
    )

    class Meta:
        model = models.Organization
        fields = (
            "accesses",
            "code",
            "country",
            "id",
            "logo",
            "representative",
            "signature",
            "title",
            "enterprise_code",
            "activity_category_code",
            "representative_profession",
            "signatory_representative",
            "signatory_representative_profession",
            "contact_phone",
            "contact_email",
            "dpo_email",
            "addresses",
        )
        read_only_fields = (
            "accesses",
            "addresses",
            "id",
        )


class AdminProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model."""

    title = serializers.CharField()
    description = serializers.CharField(
        allow_blank=True, trim_whitespace=False, required=False
    )
    call_to_action = serializers.CharField()
    price = serializers.DecimalField(
        coerce_to_string=False, decimal_places=2, max_digits=9, min_value=D(0.00)
    )
    price_currency = serializers.SerializerMethodField(read_only=True)
    instructions = serializers.CharField(
        allow_blank=True, trim_whitespace=False, required=False
    )
    certification_level = serializers.CharField(
        required=False,
        allow_blank=models.Product._meta.get_field("certification_level").blank,
        allow_null=models.Product._meta.get_field("certification_level").null,
        label=models.Product._meta.get_field("certification_level").verbose_name,
        help_text=models.Product._meta.get_field("certification_level").help_text,
    )
    teachers = serializers.SlugRelatedField(
        slug_field="id",
        queryset=models.Teacher.objects.all(),
        many=True,
        required=False,
    )
    skills = serializers.SlugRelatedField(
        slug_field="id",
        queryset=models.Skill.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = models.Product
        fields = [
            "id",
            "title",
            "description",
            "call_to_action",
            "price",
            "price_currency",
            "type",
            "instructions",
            "certificate_definition",
            "contract_definition",
            "target_courses",
            "certification_level",
            "teachers",
            "skills",
        ]
        read_only_fields = ["id"]

    def validate_certification_level(self, value):
        """
        Validate that the certification level is a positive integer or null
        """
        if not value:
            return None

        try:
            return int(value)
        except ValueError as error:
            raise serializers.ValidationError(
                "Certification level must be an integer or null."
            ) from error

    def get_price_currency(self, *args, **kwargs) -> str:
        """Return the code of currency used by the instance"""
        return settings.DEFAULT_CURRENCY

    def to_representation(self, instance):
        serializer = AdminProductDetailSerializer(instance)
        return serializer.data


class AdminProductLightSerializer(serializers.ModelSerializer):
    """Concise Serializer for Product model."""

    price = serializers.DecimalField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=D(0.00),
        read_only=True,
    )
    price_currency = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Product
        fields = [
            "id",
            "title",
            "description",
            "call_to_action",
            "price",
            "price_currency",
            "type",
            "certificate_definition",
            "contract_definition",
            "target_courses",
        ]
        read_only_fields = fields

    def get_price_currency(self, *args, **kwargs) -> str:
        """Return the code of currency used by the instance"""
        return settings.DEFAULT_CURRENCY


class AdminDiscountSerializer(serializers.ModelSerializer):
    """Admin Serializer for Discount model"""

    is_used = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Discount
        fields = ["id", "amount", "rate", "is_used"]
        read_only_fields = ["id", "is_used"]

    def get_is_used(self, discount):
        """Return the count of where the discount is used through offering rules"""
        return discount.usage_count


class AdminOfferingRuleSerializer(serializers.ModelSerializer):
    """
    Admin Serializer for OfferingRule model
    """

    nb_available_seats = serializers.SerializerMethodField(read_only=True)
    discount = AdminDiscountSerializer(read_only=False, required=False)

    class Meta:
        model = models.OfferingRule
        fields = [
            "id",
            "nb_seats",
            "is_active",
            "nb_available_seats",
            "created_on",
            "can_edit",
            "is_enabled",
            "start",
            "end",
            "discount",
            "description",
        ]
        read_only_fields = fields

    def get_nb_available_seats(self, offering_rule) -> int | None:
        """Return the number of available seats for this offering rule."""
        return offering_rule.available_seats


@extend_schema_serializer(exclude_fields=("course_product_relation",))
class AdminOfferingRuleUpdateSerializer(AdminOfferingRuleSerializer):
    """
    Admin serializer for Offering Rule reserved for partial update and update actions.

    It allows to update the field discount of an offering rule.
    """

    nb_seats = serializers.IntegerField(
        required=False,
        allow_null=True,
        label=models.OfferingRule._meta.get_field("nb_seats").verbose_name,
        help_text=models.OfferingRule._meta.get_field("nb_seats").help_text,
        default=models.OfferingRule._meta.get_field("nb_seats").default,
        min_value=models.OfferingRule._meta.get_field("nb_seats")
        .validators[0]
        .limit_value,
        max_value=models.OfferingRule._meta.get_field("nb_seats")
        .validators[1]
        .limit_value,
    )
    is_active = serializers.BooleanField(
        required=False,
        default=models.OfferingRule._meta.get_field("is_active").default,
    )
    start = serializers.DateTimeField(required=False, allow_null=True)
    end = serializers.DateTimeField(required=False, allow_null=True)
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    class Meta(AdminOfferingRuleSerializer.Meta):
        fields = [*AdminOfferingRuleSerializer.Meta.fields]

    def to_internal_value(self, data):
        """
        Override the default to_internal_value method to remove empty strings
        from the data dictionary before validation.
        """
        for key in list(data.keys()):
            if data[key] == "":
                data[key] = None
            elif key == "offering":
                data["course_product_relation"] = data.pop("offering")

        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        """Update the discount for the offering rule"""
        if discount_id := self.initial_data.get("discount_id"):
            discount = get_object_or_404(models.Discount, id=discount_id)
            validated_data["discount"] = discount
        if discount_id is None:
            instance.discount = None

        return super().update(instance, validated_data)


class AdminOfferingRuleCreateSerializer(AdminOfferingRuleUpdateSerializer):
    """
    Admin Serializer for OfferingRule model reserved to create action.

    Unlike `AdminOfferingRuleSerializer`, it allows to pass a product to create
    the offering rule. You can also add a discount.
    """

    class Meta(AdminOfferingRuleUpdateSerializer.Meta):
        fields = [
            *AdminOfferingRuleUpdateSerializer.Meta.fields,
            "course_product_relation",
        ]

    def create(self, validated_data):
        """
        Attach the discount to the offering rule.
        """
        if discount_id := self.initial_data.get("discount_id"):
            discount = get_object_or_404(models.Discount, id=discount_id)
            validated_data["discount"] = discount

        return super().create(validated_data)


class AdminCourseNestedSerializer(serializers.ModelSerializer):
    """Serializer for Course model nested in product."""

    title = serializers.CharField()
    cover = ThumbnailDetailField(required=False)
    organizations = AdminOrganizationLightSerializer(many=True, read_only=True)

    class Meta:
        model = models.Course
        fields = (
            "id",
            "code",
            "cover",
            "title",
            "organizations",
            "state",
        )
        read_only_fields = ["id", "state"]


class AdminOfferingSerializer(serializers.ModelSerializer):
    """
    Serialize all information about a course offering nested in a product.
    """

    course = AdminCourseLightSerializer(read_only=True)
    product = AdminProductLightSerializer(read_only=True)
    organizations = AdminOrganizationLightSerializer(many=True, read_only=True)
    offering_rules = AdminOfferingRuleSerializer(many=True, read_only=True)

    class Meta:
        model = models.CourseProductRelation
        fields = [
            "id",
            "can_edit",
            "course",
            "organizations",
            "offering_rules",
            "product",
            "uri",
        ]
        read_only_fields = ["id", "can_edit", "offering_rules", "uri"]

    def create(self, validated_data):
        """
        Create a new course offering and attach provided organizations to it
        """
        validation_error = {}
        course_id = self.initial_data.get("course_id")
        product_id = self.initial_data.get("product_id")

        if course_id is None:
            validation_error["course_id"] = "This field is required."
        if product_id is None:
            validation_error["product_id"] = "This field is required."

        if validation_error:
            raise serializers.ValidationError(validation_error)

        course = get_object_or_404(models.Course, id=course_id)
        validated_data["course"] = course

        product = get_object_or_404(models.Product, id=product_id)
        validated_data["product"] = product

        validated_data["organizations"] = []
        validation_error["organization_ids"] = []
        for organization_id in self.initial_data.get("organization_ids", []):
            if models.Organization.objects.filter(id=organization_id).exists():
                validated_data["organizations"].append(organization_id)
            else:
                validation_error["organization_ids"].append(
                    f"{organization_id} does not exist."
                )

        if validation_error["organization_ids"]:
            raise serializers.ValidationError(validation_error)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        if course_id := self.initial_data.get("course_id"):
            course = get_object_or_404(models.Course, id=course_id)
            validated_data["course"] = course

        if product_id := self.initial_data.get("product_id"):
            product = get_object_or_404(models.Product, id=product_id)
            validated_data["product"] = product

        validated_data["organizations"] = []
        validation_error = {"organization_ids": []}
        for organization_id in self.initial_data.get("organization_ids", []):
            if models.Organization.objects.filter(id=organization_id).exists():
                validated_data["organizations"].append(organization_id)
            else:
                validation_error["organization_ids"].append(
                    f"{organization_id} does not exist."
                )

        if validation_error["organization_ids"]:
            raise serializers.ValidationError(validation_error)

        return super().update(instance, validated_data)


class AdminCourseAccessSerializer(serializers.ModelSerializer):
    """Serializer for CourseAccess model."""

    user = AdminUserSerializer(read_only=True)
    role = serializers.ChoiceField(
        required=False,
        # choices=models.CourseAccess.ROLE_CHOICES,
        # default=enums.INSTRUCTOR,
        choices=models.CourseAccess._meta.get_field("role").choices,
        default=models.CourseAccess._meta.get_field("role").default,
    )

    class Meta:
        model = models.CourseAccess
        fields = (
            "id",
            "user",
            "role",
        )
        read_only_fields = ("id", "user")

    def validate(self, attrs):
        """
        Validate that the course access has at least a user id and a course id provided.
        """
        validated_data = super().validate(attrs)

        # Retrieve course instance from context and add it to validated_data
        course_id = self.context.get("course_id")
        validated_data["course"] = get_object_or_404(models.Course, id=course_id)

        # Retrieve user instance from context and add it to validated_data
        user_id = self.initial_data.get("user_id")
        if user_id is not None:
            try:
                validated_data["user"] = models.User.objects.get(id=user_id)
            except models.User.DoesNotExist as exception:
                raise serializers.ValidationError(
                    {"user_id": "Resource does not exist."}
                ) from exception
        elif self.partial is False and user_id is None:
            raise serializers.ValidationError({"user_id": "This field is required."})

        return validated_data


class AdminCourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model."""

    title = serializers.CharField()
    cover = ThumbnailDetailField(required=False)
    organizations = AdminOrganizationLightSerializer(many=True, read_only=True)
    offerings = AdminOfferingSerializer(many=True, read_only=True)
    accesses = AdminCourseAccessSerializer(many=True, read_only=True)
    course_runs = AdminCourseRunLightSerializer(many=True, read_only=True)
    effort = ISO8601DurationField(allow_null=True, required=False)

    class Meta:
        model = models.Course
        fields = (
            "accesses",
            "code",
            "cover",
            "course_runs",
            "id",
            "organizations",
            "offerings",
            "state",
            "title",
            "effort",
        )
        read_only_fields = (
            "accesses",
            "course_runs",
            "id",
            "state",
            "organizations",
            "offerings",
        )

    def validate(self, attrs):
        """
        Validate that the course has at least one organization provided then pass
        the list of organization ids from initial_data to validated_data until
        serializer instance accepts partial data.
        """
        validated_data = super().validate(attrs)
        validated_data["organizations"] = self.initial_data.get("organization_ids", [])
        offering = self.initial_data.get("offerings")

        if offering is not None:
            validated_data["offerings"] = []
            products = models.Product.objects.filter(
                id__in=[p["product_id"] for p in offering]
            )
            for product in products:
                offering = next(
                    (p for p in offering if p["product_id"] == str(product.id)),
                    None,
                )
                if offering is not None:
                    offering["product"] = product
                    validated_data["offerings"].append(offering)

        if self.partial is False and len(validated_data["organizations"]) == 0:
            raise serializers.ValidationError("Organizations are required.")

        return validated_data

    def create(self, validated_data):
        """
        Create a new course and attach provided organizations to it
        """
        organization_ids = validated_data.pop("organizations")
        offerings = validated_data.pop("offerings", [])
        course = super().create(validated_data)
        course.organizations.set(organization_ids)

        if len(offerings) > 0:
            for offering in offerings:
                course_offering = course.offerings.create(product=offering["product"])
                course_offering.organizations.set(organization_ids)

        return course

    def update(self, instance, validated_data):
        """
        Attach provided organizations to the course instance then update it.
        """
        if len(validated_data.get("organizations")) == 0:
            organizations_ids = validated_data.pop("organizations")
            instance.organizations.set(organizations_ids)

        if validated_data.get("offerings") is not None:
            offerings = validated_data.pop("offerings")
            if len(offerings) == 0:
                instance.offerings.all().delete()

            else:
                for offering in offerings:
                    (relation, _) = instance.offerings.get_or_create(
                        product=offering["product"]
                    )
                    relation.organizations.set(offering["organization_ids"])

        return super().update(instance, validated_data)


class AdminCourseRunSerializer(AdminCourseRunLightSerializer):
    """Serializer for CourseRun model."""

    course = AdminCourseLightSerializer(read_only=True)

    class Meta:
        model = AdminCourseRunLightSerializer.Meta.model
        fields = AdminCourseRunLightSerializer.Meta.fields + ["course"]

    def validate(self, attrs):
        """
        Validate that the course run has a course provided then bind the course instance
        to validated_data until serializer instance accepts partial data.
        """
        validated_data = super().validate(attrs)
        course_id = self.initial_data.get("course_id", None)

        if self.partial is False and course_id is None:
            raise serializers.ValidationError(
                {"course_id": "This field cannot be null."}
            )

        if course_id:
            try:
                validated_data["course"] = models.Course.objects.get(id=course_id)
            except models.Course.DoesNotExist as exception:
                raise serializers.ValidationError(
                    {"course_id": "Resource {course_id} does not exist."}, exception
                ) from exception

        return validated_data


class AdminTargetCourseSerializer(serializers.ModelSerializer):
    """
    Serialize all information about a target course.
    """

    course_runs = serializers.SerializerMethodField(read_only=True)
    position = serializers.SerializerMethodField(read_only=True)
    is_graded = serializers.SerializerMethodField(read_only=True)
    organizations = AdminOrganizationLightSerializer(many=True, read_only=True)

    class Meta:
        model = models.Course
        fields = [
            "id",
            "code",
            "course_runs",
            "is_graded",
            "organizations",
            "position",
            "title",
        ]
        read_only_fields = [
            "id",
            "code",
            "course_runs",
            "is_graded",
            "organizations",
            "position",
            "title",
        ]

    @property
    def context_resource(self):
        """
        Retrieve the product/order resource provided in context.
        If no product/order is provided, it raises a ValidationError.
        """
        try:
            resource = self.context["resource"]
        except KeyError as exception:
            raise serializers.ValidationError(
                'TargetCourseSerializer context must contain a "resource" property.'
            ) from exception

        if not isinstance(resource, (models.Order, models.Product)):
            raise serializers.ValidationError(
                "TargetCourseSerializer context resource property must be instance of "
                "Product or Order."
            )

        return resource

    def get_target_course_relation(self, target_course):
        """
        Return the relevant target course offering depending on whether the resource context
        is a product or an order.
        """
        if isinstance(self.context_resource, models.Order):
            return target_course.order_relations.get(order=self.context_resource)

        if isinstance(self.context_resource, models.Product):
            return target_course.product_target_relations.get(
                product=self.context_resource
            )

        return None

    def get_position(self, target_course):
        """
        Retrieve the position of the course related to its product/order offering
        """
        offering = self.get_target_course_relation(target_course)

        return offering.position

    def get_is_graded(self, target_course):
        """
        Retrieve the `is_graded` state of the course related to its product/order offering
        """
        offering = self.get_target_course_relation(target_course)

        return offering.is_graded

    def get_course_runs(self, target_course) -> list[dict]:
        """
        Return related course runs ordered by start date asc
        """
        course_runs = self.context_resource.target_course_runs.filter(
            course=target_course
        ).order_by("start")

        return AdminCourseRunSerializer(course_runs, many=True).data


class AdminProductTargetCourseRelationDisplaySerializer(serializers.ModelSerializer):
    """
    Serializer for ProductTargetCourseRelation model
    """

    course = AdminCourseLightSerializer()
    course_runs = AdminCourseRunSerializer(many=True)

    class Meta:
        model = models.ProductTargetCourseRelation
        fields = ["id", "course", "is_graded", "position", "course_runs"]


class AdminProductTargetCourseRelationSerializer(serializers.ModelSerializer):
    """
    Serializer for ProductTargetCourseRelation model
    """

    is_graded = serializers.BooleanField(
        required=False,
        default=models.ProductTargetCourseRelation._meta.get_field("is_graded").default,
        label=models.ProductTargetCourseRelation._meta.get_field(
            "is_graded"
        ).verbose_name,
        help_text=models.ProductTargetCourseRelation._meta.get_field(
            "is_graded"
        ).help_text,
    )
    position = serializers.IntegerField(
        required=False,
        default=models.ProductTargetCourseRelation._meta.get_field("position").default,
        label=models.ProductTargetCourseRelation._meta.get_field(
            "position"
        ).verbose_name,
        min_value=models.ProductTargetCourseRelation._meta.get_field("position")
        .validators[0]
        .limit_value,
        max_value=models.ProductTargetCourseRelation._meta.get_field("position")
        .validators[1]
        .limit_value,
    )

    class Meta:
        model = models.ProductTargetCourseRelation
        fields = ["id", "course", "product", "is_graded", "position", "course_runs"]

    def to_representation(self, instance):
        serializer = AdminProductTargetCourseRelationDisplaySerializer(instance)
        return serializer.data


class AdminProductTargetCourseRelationNestedSerializer(serializers.ModelSerializer):
    """
    Serializer for ProductTargetCourseRelation model
    """

    course = AdminCourseLightSerializer()
    course_runs = AdminCourseRunLightSerializer(read_only=True, many=True)

    class Meta:
        model = models.ProductTargetCourseRelation
        fields = ["id", "course", "course_runs", "is_graded", "position"]
        read_only_fields = ["id", "course", "course_runs", "is_graded", "position"]


class AdminTeacherSerializer(serializers.ModelSerializer):
    """Serializer for Teacher model."""

    class Meta:
        model = models.Teacher
        fields = ["id", "first_name", "last_name"]
        read_only_fields = ["id"]


class AdminSkillSerializer(serializers.ModelSerializer):
    """Serializer for Skill model."""

    title = serializers.CharField()

    class Meta:
        model = models.Skill
        fields = ["id", "title"]
        read_only_fields = ["id"]


class AdminProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for Product details"""

    certificate_definition = AdminCertificateDefinitionSerializer(read_only=True)
    contract_definition = AdminContractDefinitionSerializer(read_only=True)
    target_courses = serializers.SerializerMethodField(read_only=True)
    price = serializers.DecimalField(
        coerce_to_string=False, decimal_places=2, max_digits=9, min_value=D(0.00)
    )
    offerings = AdminOfferingSerializer(read_only=True, many=True)
    price_currency = serializers.SerializerMethodField(read_only=True)
    certification_level = serializers.IntegerField(read_only=True)
    skills = AdminSkillSerializer(many=True, read_only=True)
    teachers = AdminTeacherSerializer(many=True, read_only=True)

    class Meta:
        model = models.Product
        fields = [
            "id",
            "title",
            "description",
            "call_to_action",
            "type",
            "price",
            "price_currency",
            "certificate_definition",
            "contract_definition",
            "target_courses",
            "offerings",
            "certification_level",
            "instructions",
            "teachers",
            "skills",
        ]
        read_only_fields = fields

    def get_target_courses(self, product):
        """Compute the serialized value for the "target_courses" field."""
        context = self.context.copy()
        context["resource"] = product

        offerings = models.ProductTargetCourseRelation.objects.filter(
            product=product
        ).order_by("position")

        return AdminProductTargetCourseRelationNestedSerializer(
            instance=offerings, many=True, context=context
        ).data

    def get_price_currency(self, *args, **kwargs) -> str:
        """Return the code of currency used by the instance"""
        return settings.DEFAULT_CURRENCY


class AdminOrderEnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Enrollment Order model
    """

    course_run = AdminCourseRunLightSerializer(read_only=True)

    class Meta:
        model = models.Enrollment
        fields = [
            "course_run",
            "created_on",
            "id",
            "is_active",
            "state",
            "updated_on",
            "was_created_by_order",
        ]
        read_only_fields = fields


class AdminContractSerializer(serializers.ModelSerializer):
    """Read only serializer for Contract model."""

    definition_title = serializers.SlugRelatedField(
        read_only=True, slug_field="title", source="definition"
    )

    class Meta:
        model = models.Contract
        fields = [
            "id",
            "definition_title",
            "student_signed_on",
            "organization_signed_on",
            "submitted_for_signature_on",
        ]
        read_only_fields = fields


class AdminCertificateSerializer(serializers.ModelSerializer):
    """Read only serializer for Certificate model."""

    definition_title = serializers.SlugRelatedField(
        read_only=True, slug_field="title", source="certificate_definition"
    )

    class Meta:
        model = models.Certificate
        fields = [
            "id",
            "definition_title",
            "issued_on",
        ]
        read_only_fields = fields


@extend_schema_serializer(component_name="AdminInvoiceSerializer")
class BaseAdminInvoiceSerializer(serializers.ModelSerializer):
    """Base read only serializer for Invoice model."""

    recipient_address = serializers.SerializerMethodField(read_only=True)
    total = serializers.DecimalField(
        coerce_to_string=False, decimal_places=2, max_digits=9
    )
    total_currency = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = payment_models.Invoice
        fields = [
            "id",
            "balance",
            "created_on",
            "invoiced_balance",
            "recipient_address",
            "reference",
            "state",
            "transactions_balance",
            "total",
            "total_currency",
            "type",
            "updated_on",
        ]
        read_only_fields = fields

    def get_recipient_address(self, invoice):
        """Return the serialized recipient address."""
        return f"{invoice.recipient_address.full_name}\n{invoice.recipient_address.full_address}"

    def get_total_currency(self, *args, **kwargs) -> str:
        """Return the code of currency used by the instance"""
        return settings.DEFAULT_CURRENCY


class AdminInvoiceSerializer(BaseAdminInvoiceSerializer):
    """Read only serializer for Invoice model."""

    children = BaseAdminInvoiceSerializer(many=True, read_only=True)

    class Meta(BaseAdminInvoiceSerializer.Meta):
        fields = BaseAdminInvoiceSerializer.Meta.fields + ["children"]
        read_only_fields = fields


class AdminOrderPaymentSerializer(serializers.Serializer):
    """
    Serializer for the order payment
    """

    id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=D(0.00),
        required=True,
    )
    currency = serializers.SerializerMethodField(read_only=True)
    due_date = serializers.DateField(required=True)
    state = serializers.ChoiceField(
        choices=enums.PAYMENT_STATE_CHOICES,
        required=True,
    )

    def to_internal_value(self, data):
        """Used to format the amount and the due_date before validation."""
        return super().to_internal_value(
            {
                "id": str(data.get("id")),
                "amount": data.get("amount").amount_as_string(),
                "due_date": data.get("due_date").isoformat(),
                "state": data.get("state"),
            }
        )

    def get_currency(self, *args, **kwargs) -> str:
        """Return the code of currency used by the instance"""
        return settings.DEFAULT_CURRENCY

    def create(self, validated_data):
        """Only there to avoid a NotImplementedError"""

    def update(self, instance, validated_data):
        """Only there to avoid a NotImplementedError"""


class AdminCreditCardSerializer(serializers.ModelSerializer):
    """Read only Serializer for CreditCard model."""

    class Meta:
        model = payment_models.CreditCard
        fields = [
            "id",
            "brand",
            "expiration_month",
            "expiration_year",
            "last_numbers",
        ]
        read_only_fields = fields


class AdminOrderSerializer(serializers.ModelSerializer):
    """Read only Serializer for Order model."""

    product = AdminProductLightSerializer(read_only=True)
    course = AdminCourseLightSerializer(read_only=True)
    enrollment = AdminOrderEnrollmentSerializer(read_only=True)
    owner = AdminUserSerializer(read_only=True)
    total = serializers.DecimalField(
        coerce_to_string=False, decimal_places=2, max_digits=9, min_value=D(0.00)
    )
    total_currency = serializers.SerializerMethodField(read_only=True)
    contract = AdminContractSerializer()
    certificate = AdminCertificateSerializer()
    main_invoice = AdminInvoiceSerializer()
    organization = AdminOrganizationLightSerializer(read_only=True)
    offering_rules = AdminOfferingRuleSerializer(read_only=True, many=True)
    payment_schedule = AdminOrderPaymentSerializer(many=True, read_only=True)
    credit_card = AdminCreditCardSerializer(read_only=True)
    has_waived_withdrawal_right = serializers.BooleanField(read_only=True)

    class Meta:
        model = models.Order
        fields = (
            "id",
            "created_on",
            "state",
            "owner",
            "product",
            "course",
            "enrollment",
            "organization",
            "offering_rules",
            "total",
            "total_currency",
            "contract",
            "certificate",
            "main_invoice",
            "payment_schedule",
            "credit_card",
            "has_waived_withdrawal_right",
        )
        read_only_fields = fields

    def get_total_currency(self, *args, **kwargs) -> str:
        """Return the code of currency used by the instance"""
        return settings.DEFAULT_CURRENCY


class AdminOrderLightSerializer(serializers.ModelSerializer):
    """
    Read only light serializer for Order model.
    """

    product_title = serializers.SlugRelatedField(
        read_only=True, slug_field="title", source="product"
    )
    course_code = serializers.SlugRelatedField(
        read_only=True, slug_field="code", source="course"
    )
    enrollment_id = serializers.SlugRelatedField(
        read_only=True, slug_field="id", source="enrollment"
    )
    organization_title = serializers.SlugRelatedField(
        read_only=True, slug_field="title", source="organization"
    )
    owner_name = serializers.SerializerMethodField(read_only=True)
    total = serializers.DecimalField(
        coerce_to_string=False, decimal_places=2, max_digits=9, min_value=D(0.00)
    )
    total_currency = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Order
        fields = (
            "course_code",
            "created_on",
            "updated_on",
            "enrollment_id",
            "id",
            "organization_title",
            "owner_name",
            "product_title",
            "state",
            "total",
            "total_currency",
            "discount",
        )
        read_only_fields = fields

    def get_total_currency(self, *args, **kwargs) -> str:
        """Return the code of currency used by the instance"""
        return get_default_currency_symbol()

    def get_owner_name(self, instance) -> str:
        """
        Return the full name of the order's owner if available,
        otherwise fallback to the username
        """
        return instance.owner.name


class AdminOrderExportSerializer(serializers.ModelSerializer):  # pylint: disable=too-many-public-methods
    """
    Read only light serializer for Order export.
    """

    class Meta:
        model = models.Order
        fields_labels = [
            ("id", _("Order reference")),
            ("product", _("Product")),
            ("owner_name", _("Owner")),
            ("owner_email", _("Email")),
            ("organization", _("Organization")),
            ("state", _("Order state")),
            ("created_on", _("Creation date")),
            ("updated_on", _("Last modification date")),
            ("product_type", _("Product type")),
            ("enrollment_course_run_title", _("Enrollment session")),
            ("enrollment_course_run_state", _("Session status")),
            ("enrollment_created_on", _("Enrolled on")),
            ("total", _("Price")),
            ("total_currency", _("Currency")),
            ("discount", _("Discount")),
            ("has_waived_withdrawal_right", _("Waived withdrawal right")),
            ("certificate", _("Certificate generated for this order")),
            ("contract", _("Contract")),
            ("contract_submitted_for_signature_on", _("Submitted for signature")),
            ("contract_student_signed_on", _("Student signature date")),
            ("contract_organization_signed_on", _("Organization signature date")),
            ("main_invoice_type", _("Type")),
            ("main_invoice_total", _("Total (on invoice)")),
            ("main_invoice_balance", _("Balance (on invoice)")),
            ("main_invoice_state", _("Billing state")),
            ("credit_card_brand", _("Card type")),
            ("credit_card_last_numbers", _("Last card digits")),
            ("credit_card_expiration_date", _("Card expiration date")),
        ]
        for i in range(1, 5):
            fields_labels.append(
                (f"installment_due_date_{i}", _("Installment date %d") % i)
            )
            fields_labels.append(
                (f"installment_amount_{i}", _("Installment amount %d") % i)
            )
            fields_labels.append(
                (f"installment_state_{i}", _("Installment state %d") % i)
            )
        fields = [field for field, label in fields_labels]
        read_only_fields = fields

    @property
    def headers(self):
        """
        Return the headers of the CSV file.
        """
        return [label for field, label in self.Meta.fields_labels]

    product = serializers.SlugRelatedField(read_only=True, slug_field="title")
    owner_name = serializers.SerializerMethodField(read_only=True)
    owner_email = serializers.SlugRelatedField(
        read_only=True, slug_field="email", source="owner"
    )
    organization = serializers.SlugRelatedField(read_only=True, slug_field="title")
    created_on = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")
    updated_on = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")
    product_type = serializers.SlugRelatedField(
        read_only=True, slug_field="type", source="product"
    )
    enrollment_course_run_title = serializers.SlugRelatedField(
        read_only=True, slug_field="course_run__title", source="enrollment"
    )
    enrollment_course_run_state = serializers.SlugRelatedField(
        read_only=True, slug_field="course_run__state", source="enrollment"
    )
    enrollment_created_on = serializers.SerializerMethodField(read_only=True)
    total_currency = serializers.SerializerMethodField(read_only=True)
    discount = serializers.SerializerMethodField(read_only=True)
    has_waived_withdrawal_right = serializers.SerializerMethodField(read_only=True)
    certificate = serializers.SerializerMethodField(read_only=True)

    contract = serializers.SlugRelatedField(
        read_only=True, slug_field="definition__title"
    )
    contract_submitted_for_signature_on = serializers.SerializerMethodField(
        read_only=True
    )
    contract_student_signed_on = serializers.SerializerMethodField(read_only=True)
    contract_organization_signed_on = serializers.SerializerMethodField(read_only=True)
    main_invoice_type = serializers.SlugRelatedField(
        read_only=True, slug_field="type", source="main_invoice"
    )
    main_invoice_total = serializers.SlugRelatedField(
        read_only=True, slug_field="total", source="main_invoice"
    )
    main_invoice_balance = serializers.SlugRelatedField(
        read_only=True, slug_field="balance", source="main_invoice"
    )
    main_invoice_state = serializers.SlugRelatedField(
        read_only=True, slug_field="state", source="main_invoice"
    )
    credit_card_brand = serializers.SlugRelatedField(
        read_only=True, slug_field="brand", source="credit_card"
    )
    credit_card_last_numbers = serializers.SlugRelatedField(
        read_only=True, slug_field="last_numbers", source="credit_card"
    )
    credit_card_expiration_date = serializers.SerializerMethodField(read_only=True)

    installment_due_date_1 = serializers.SerializerMethodField(read_only=True)
    installment_amount_1 = serializers.SerializerMethodField(read_only=True)
    installment_state_1 = serializers.SerializerMethodField(read_only=True)
    installment_due_date_2 = serializers.SerializerMethodField(read_only=True)
    installment_amount_2 = serializers.SerializerMethodField(read_only=True)
    installment_state_2 = serializers.SerializerMethodField(read_only=True)
    installment_due_date_3 = serializers.SerializerMethodField(read_only=True)
    installment_amount_3 = serializers.SerializerMethodField(read_only=True)
    installment_state_3 = serializers.SerializerMethodField(read_only=True)
    installment_due_date_4 = serializers.SerializerMethodField(read_only=True)
    installment_amount_4 = serializers.SerializerMethodField(read_only=True)
    installment_state_4 = serializers.SerializerMethodField(read_only=True)

    def get_owner_name(self, instance) -> str:
        """
        Return the full name of the order's owner if available,
        otherwise fallback to the username
        """
        return instance.owner.name

    def get_enrollment_created_on(self, instance) -> str:
        """
        Return the creation date of the enrollment if available,
        otherwise an empty string.
        """
        if not instance.enrollment:
            return ""
        return instance.enrollment.created_on.strftime("%d/%m/%Y %H:%M:%S")

    def get_total_currency(self, *args, **kwargs) -> str:
        """Return the code of currency used by the instance"""
        return settings.DEFAULT_CURRENCY

    def get_discount(self, instance) -> str:
        """
        Return the discount when available on the order,
        otherwise return an empty string
        """
        return instance.discount or ""

    def get_has_waived_withdrawal_right(self, instance) -> str:
        """
        Return "Yes" if the order has waived the withdrawal right, otherwise "No".
        """
        return "Yes" if instance.has_waived_withdrawal_right else "No"

    def get_certificate(self, instance) -> str:
        """
        Return "Yes" if a certificate has been generated for the order, otherwise "No".
        """
        return "Yes" if hasattr(instance, "certificate") else "No"

    def get_contract_date(self, instance, date_field: str) -> str:
        """
        Return the date of the specified contract field if available,
        otherwise an empty string.
        """
        try:
            return getattr(instance.contract, date_field).strftime("%d/%m/%Y %H:%M:%S")
        except (models.Contract.DoesNotExist, AttributeError):
            return ""

    def get_contract_submitted_for_signature_on(self, instance) -> str:
        """
        Return the date the contract was submitted for signature if available,
        otherwise an empty string.
        """
        return self.get_contract_date(instance, "submitted_for_signature_on")

    def get_contract_student_signed_on(self, instance) -> str:
        """
        Return the date the student signed the contract if available,
        otherwise an empty string.
        """
        return self.get_contract_date(instance, "student_signed_on")

    def get_contract_organization_signed_on(self, instance) -> str:
        """
        Return the date the organization signed the contract if available,
        otherwise an empty string.
        """
        return self.get_contract_date(instance, "organization_signed_on")

    def get_credit_card_expiration_date(self, instance) -> str:
        """
        Return the expiration date of the credit card if available,
        otherwise an empty string.
        """
        if not instance.credit_card:
            return ""
        month = instance.credit_card.expiration_month
        year = instance.credit_card.expiration_year
        return f"{month}/{year}"

    def get_installment_value(self, instance, index, field) -> str:
        """
        Return the value of the specified field for the specified installment if available,
        otherwise an empty string.
        """
        index -= 1
        try:
            value = instance.payment_schedule[index][field]
            if field == "due_date":
                return value.strftime("%d/%m/%Y %H:%M:%S")
            return value
        except (IndexError, KeyError, TypeError):
            return ""

    def get_installment_due_date_1(self, instance) -> str:
        """
        Return the due date of the first installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 1, "due_date")

    def get_installment_amount_1(self, instance) -> str:
        """
        Return the amount of the first installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 1, "amount")

    def get_installment_state_1(self, instance) -> str:
        """
        Return the state of the first installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 1, "state")

    def get_installment_due_date_2(self, instance) -> str:
        """
        Return the due date of the second installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 2, "due_date")

    def get_installment_amount_2(self, instance) -> str:
        """
        Return the amount of the second installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 2, "amount")

    def get_installment_state_2(self, instance) -> str:
        """
        Return the state of the second installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 2, "state")

    def get_installment_due_date_3(self, instance) -> str:
        """
        Return the due date of the third installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 3, "due_date")

    def get_installment_amount_3(self, instance) -> str:
        """
        Return the amount of the third installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 3, "amount")

    def get_installment_state_3(self, instance) -> str:
        """
        Return the state of the third installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 3, "state")

    def get_installment_due_date_4(self, instance) -> str:
        """
        Return the due date of the fourth installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 4, "due_date")

    def get_installment_amount_4(self, instance) -> str:
        """
        Return the amount of the fourth installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 4, "amount")

    def get_installment_state_4(self, instance) -> str:
        """
        Return the state of the fourth installment if available,
        otherwise an empty string.
        """
        return self.get_installment_value(instance, 4, "state")


class AdminOrderListExportSerializer(serializers.ListSerializer):
    """
    Serializer for exporting a list of orders to a CSV stream.
    """

    def update(self, instance, validated_data):
        """
        Only there to avoid a NotImplementedError.
        """

    def csv_stream(self):
        """
        Return a CSV stream of the serialized data.
        """
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        yield writer.writerow(self.child.headers)
        for row in self.data:
            yield writer.writerow(row.values())


class AdminBatchOrderSerializer(serializers.ModelSerializer):
    """Admin Batch Order Serializer"""

    owner = serializers.SlugRelatedField(
        queryset=models.User.objects.all(),
        slug_field="id",
    )
    total = serializers.DecimalField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=D(0.00),
        read_only=True,
    )
    currency = serializers.SerializerMethodField(read_only=True)
    relation = serializers.SlugRelatedField(
        queryset=models.CourseProductRelation.objects.all(),
        slug_field="id",
        write_only=False,
    )
    organization = AdminOrganizationLightSerializer(read_only=True)
    main_invoice_reference = serializers.SlugRelatedField(
        read_only=True, slug_field="reference", source="main_invoice"
    )
    voucher = serializers.SlugRelatedField(
        queryset=models.Voucher.objects.all(),
        slug_field="code",
        required=False,
    )
    country = CountryField(required=False)
    nb_seats = serializers.IntegerField(
        min_value=1,
        help_text="The number of seats to reserve",
    )
    trainees = serializers.JSONField(default=list)
    offering_rules = AdminOfferingRuleSerializer(read_only=True, many=True)
    vouchers = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.BatchOrder
        fields = [
            "id",
            "owner",
            "total",
            "currency",
            "relation",
            "organization",
            "main_invoice_reference",
            "contract_id",
            "company_name",
            "identification_number",
            "address",
            "postcode",
            "city",
            "country",
            "nb_seats",
            "trainees",
            "voucher",
            "vouchers",
            "offering_rules",
        ]
        read_only_fields = [
            "id",
            "total",
            "currency",
            "main_invoice_reference",
            "contract_id",
            "offering_rules",
            "vouchers",
        ]

    def get_currency(self, *args, **kwargs) -> str:
        """
        Return the currency used
        """
        return settings.DEFAULT_CURRENCY

    def get_vouchers(self, instance) -> list:
        """Return the voucher codes generated"""
        return instance.vouchers

    def to_internal_value(self, data):
        """
        Override to ensure that the 'offering' field is renamed to 'relation'
        for consistency with the model field.
        """
        data["relation"] = data.pop("offering", None)
        return super().to_internal_value(data)

    def to_representation(self, instance):
        """
        Override to ensure that the 'relation' field is renamed to 'offering'
        for consistency with the model field.
        """
        representation = super().to_representation(instance)
        representation["offering"] = representation.pop("relation", None)
        return representation

    def create(self, validated_data):
        """
        When an organization is passed, we should add it to the validated data,
        otherwise, we should set the organization with the least active orders.
        Verify that the number of available seats in offering rules of the course
        product offering is sufficient to meet the required seats specified in
        the batch order.
        """
        relation = validated_data.get("relation")
        if organization_id := self.initial_data.get("organization", None):
            if models.Organization.objects.filter(id=organization_id).exists():
                validated_data["organization_id"] = organization_id
            else:
                raise serializers.ValidationError(
                    {"organization_id": "Resource does not exist."}
                )
        else:
            validated_data["organization_id"] = get_least_active_organization(
                relation.product, relation.course
            ).id

        nb_seats = validated_data.get("nb_seats")
        validated_data.setdefault("offering_rules", [])
        try:
            offering_rule = get_active_offering_rule(relation.id, nb_seats)
        except ValueError as exception:
            raise serializers.ValidationError(
                {
                    "offering_rule": [
                        "Maximum number of orders reached for "
                        f"product {relation.product.title:s}"
                    ]
                }
            ) from exception
        if offering_rule:
            validated_data["offering_rules"].append(offering_rule)

        return super().create(validated_data)


class AdminEnrollmentLightSerializer(serializers.ModelSerializer):
    """
    Light Serializer for Enrollment model
    """

    course_run = AdminCourseRunLightSerializer(read_only=True)
    user_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Enrollment
        fields = [
            "id",
            "course_run",
            "user_name",
            "state",
            "is_active",
        ]
        read_only_fields = fields

    def get_user_name(self, instance) -> str:
        """
        Return the full name of the enrollment's user if available,
        otherwise fallback to the username
        """
        return instance.user.name


class AdminEnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Enrollment model
    """

    course_run = AdminCourseRunLightSerializer(read_only=True)
    user = AdminUserSerializer(read_only=True)
    certificate = AdminCertificateSerializer(read_only=True)

    class Meta:
        model = models.Enrollment
        fields = [
            "course_run",
            "created_on",
            "certificate",
            "id",
            "is_active",
            "state",
            "updated_on",
            "user",
            "was_created_by_order",
        ]
        read_only_fields = [
            "course_run",
            "created_on",
            "certificate",
            "id",
            "state",
            "updated_on",
            "user",
            "was_created_by_order",
        ]

    def validate(self, attrs):
        """
        Check whether the required data is passed and if the course run and the user
        both exist. The course run can be opened or closed, and the admin user can
        create/update the enrollment of a user.
        """
        validated_data = super().validate(attrs)

        try:
            course_run_id = self.initial_data["course_run"]
        except KeyError as exception:
            message = "You must provide a course_run_id to create/update an enrollment."
            raise serializers.ValidationError({"__all__": [message]}) from exception

        try:
            course_run = models.CourseRun.objects.get(id=course_run_id)
        except models.CourseRun.DoesNotExist as exception:
            message = f'A course run with id "{course_run_id}" does not exist.'
            raise serializers.ValidationError({"__all__": [message]}) from exception

        try:
            user_id = self.initial_data["user"]
        except KeyError as exception:
            message = "You must provide a user_id to create/update an enrollment."
            raise serializers.ValidationError({"__all__": [message]}) from exception

        try:
            user = models.User.objects.get(id=user_id)
        except models.User.DoesNotExist as exception:
            message = f'A user with the id "{user_id}" does not exist.'
            raise serializers.ValidationError({"__all__": [message]}) from exception

        validated_data["course_run"] = course_run
        validated_data["user"] = user

        return validated_data

    def update(self, instance, validated_data):
        """
        Only `is_active` field can be updated on an existing enrollment.
        The `was_created_by_order` field should be updated only if the enrollment
        was previously inactive only.
        """
        if instance.is_active is True:
            validated_data.pop("was_created_by_order", None)

        return super().update(instance, validated_data)
