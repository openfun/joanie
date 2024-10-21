# ruff: noqa: SLF001
# pylint: disable=too-many-lines
"""Client serializers for Joanie Core app."""

from decimal import Decimal as D

from django.conf import settings
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

import markdown
from drf_spectacular.utils import extend_schema_field
from rest_framework import exceptions, serializers
from rest_framework.generics import get_object_or_404

from joanie.core import enums, models
from joanie.core.serializers.base import CachedModelSerializer
from joanie.core.serializers.fields import ISO8601DurationField, ThumbnailDetailField
from joanie.payment.models import CreditCard


class AbilitiesModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `exclude` argument that
    dynamically controls which fields should be excluded from the serializer.
    """

    def __init__(self, *args, **kwargs):
        """Exclude fields after class instanciation."""
        self.exclude_abilities = kwargs.pop("exclude_abilities", None)
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        """Add abilities except when the serializer is nested."""
        representation = super().to_representation(instance)
        request = self.context.get("request")
        if request and not self.exclude_abilities:
            representation["abilities"] = instance.get_abilities(request.user)
        return representation


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

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
        ]
        read_only_fields = fields

    def get_abilities(self, user) -> dict:
        """Return abilities of the logged-in user on itself."""
        request = self.context.get("request")
        if request:
            return request.user.get_abilities(user)
        return {}


class AddressSerializer(serializers.ModelSerializer):
    """
    Address model serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    is_main = serializers.BooleanField(
        required=False,
        label=models.Address._meta.get_field("is_main").verbose_name,
    )

    class Meta:
        model = models.Address
        fields = [
            "address",
            "city",
            "country",
            "first_name",
            "last_name",
            "id",
            "is_main",
            "postcode",
            "title",
        ]
        read_only_fields = [
            "id",
        ]


class CourseLightSerializer(AbilitiesModelSerializer):
    """
    Serialize all non-sensitive course information. This serializer is read only.
    """

    cover = ThumbnailDetailField()

    class Meta:
        model = models.Course
        fields = [
            "code",
            "cover",
            "id",
            "title",
        ]
        read_only_fields = fields


class CourseAccessSerializer(AbilitiesModelSerializer):
    """Serialize course accesses for the API."""

    user_id = serializers.SlugRelatedField(
        queryset=models.User.objects.all(),
        slug_field="id",
        source="user",
    )

    role = serializers.ChoiceField(
        required=False,
        choices=models.CourseAccess._meta.get_field("role").choices,
        default=models.CourseAccess._meta.get_field("role").default,
    )

    class Meta:
        model = models.CourseAccess
        fields = ["id", "role", "user_id"]
        read_only_fields = ["id"]

    def update(self, instance, validated_data):
        """Make "user" field readonly but only on update."""
        validated_data.pop("user", None)
        return super().update(instance, validated_data)

    # pylint: disable=too-many-boolean-expressions
    def validate(self, attrs):
        """
        Check access rights specific to writing (create/update)
        """
        request = self.context.get("request")
        user = getattr(request, "user", None)
        role = attrs.get("role")

        # Update
        if self.instance:
            can_set_role_to = self.instance.get_abilities(user)["set_role_to"]

            if role and role not in can_set_role_to:
                message = (
                    _(
                        f"You are only allowed to set role to {', '.join(can_set_role_to)}"
                    )
                    if can_set_role_to
                    else _("You are not allowed to set this role for this course.")
                )
                raise exceptions.PermissionDenied(message)

        # Create
        else:
            try:
                course_id = self.context["course_id"]
            except KeyError as exc:
                raise exceptions.ValidationError(
                    _(
                        "You must set a course ID in context to create a new course access."
                    )
                ) from exc

            if not models.CourseAccess.objects.filter(
                course=course_id,
                user=user,
                role__in=[enums.OWNER, enums.ADMIN],
            ).exists():
                raise exceptions.PermissionDenied(
                    _("You are not allowed to manage accesses for this course.")
                )

            if (
                role == enums.OWNER
                and not models.CourseAccess.objects.filter(
                    course=course_id,
                    user=user,
                    role=enums.OWNER,
                ).exists()
            ):
                raise exceptions.PermissionDenied(
                    "Only owners of a course can assign other users as owners."
                )

        attrs["course_id"] = self.context["course_id"]
        return attrs


class OrganizationSerializer(AbilitiesModelSerializer):
    """
    Serialize all non-sensitive information about an organization
    """

    logo = ThumbnailDetailField(allow_null=True)
    address = serializers.SerializerMethodField(allow_null=True)

    class Meta:
        model = models.Organization
        fields = [
            "id",
            "code",
            "logo",
            "title",
            "address",
            "enterprise_code",
            "activity_category_code",
            "contact_phone",
            "contact_email",
            "dpo_email",
        ]
        read_only_fields = fields

    @extend_schema_field(AddressSerializer)
    def get_address(self, instance) -> dict | None:
        """Return only the main address of the organization."""
        main_address = instance.addresses.filter(is_main=True, is_reusable=True).first()
        return AddressSerializer(main_address).data if main_address else None


class OrganizationAccessSerializer(AbilitiesModelSerializer):
    """Serialize Organization accesses for the API."""

    user_id = serializers.SlugRelatedField(
        queryset=models.User.objects.all(),
        slug_field="id",
        source="user",
    )

    role = serializers.ChoiceField(
        required=False,
        choices=models.OrganizationAccess._meta.get_field("role").choices,
        default=models.OrganizationAccess._meta.get_field("role").default,
    )

    class Meta:
        model = models.OrganizationAccess
        fields = ["id", "role", "user_id"]
        read_only_fields = ["id"]

    def update(self, instance, validated_data):
        """Make "user" field is readonly but only on update."""
        validated_data.pop("user", None)
        return super().update(instance, validated_data)

    # pylint: disable=too-many-boolean-expressions
    def validate(self, attrs):
        """
        Check access rights specific to writing (create/update)
        """
        request = self.context.get("request")
        user = getattr(request, "user", None)
        role = attrs.get("role")

        # Update
        if self.instance:
            can_set_role_to = self.instance.get_abilities(user)["set_role_to"]

            if role and role not in can_set_role_to:
                message = (
                    _(
                        f"You are only allowed to set role to {', '.join(can_set_role_to)}"
                    )
                    if can_set_role_to
                    else _("You are not allowed to set this role for this course.")
                )
                raise exceptions.PermissionDenied(message)

        # Create
        else:
            try:
                organization_id = self.context["organization_id"]
            except KeyError as exc:
                raise exceptions.ValidationError(
                    _(
                        "You must set a organization ID in context to create a new "
                        "organization access."
                    )
                ) from exc

            if not models.OrganizationAccess.objects.filter(
                organization=organization_id,
                user=user,
                role__in=[enums.OWNER, enums.ADMIN],
            ).exists():
                raise exceptions.PermissionDenied(
                    _("You are not allowed to manage accesses for this organization.")
                )

            if (
                role == enums.OWNER
                and not models.OrganizationAccess.objects.filter(
                    organization=organization_id,
                    user=user,
                    role=enums.OWNER,
                ).exists()
            ):
                raise exceptions.PermissionDenied(
                    "Only owners of an organization can assign other users as owners."
                )

        attrs["organization_id"] = self.context["organization_id"]
        return attrs


class CourseRunSerializer(serializers.ModelSerializer):
    """
    Serialize all information about a course run
    """

    course = CourseLightSerializer(read_only=True, exclude_abilities=True)

    class Meta:
        model = models.CourseRun
        fields = [
            "course",
            "end",
            "enrollment_end",
            "enrollment_start",
            "id",
            "languages",
            "resource_link",
            "start",
            "title",
            "state",
        ]
        read_only_fields = fields


class EnrollmentLightSerializer(serializers.ModelSerializer):
    """
    Enrollment model light serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    course_run = CourseRunSerializer(read_only=True)
    was_created_by_order = serializers.BooleanField(required=True)

    class Meta:
        model = models.Enrollment
        fields = [
            "id",
            "course_run",
            "created_on",
            "is_active",
            "state",
            "was_created_by_order",
        ]
        read_only_fields = fields


class NestedOrderSerializer(serializers.ModelSerializer):
    """
    Order model serializer for the Certificate model
    """

    id = serializers.CharField(read_only=True, required=False)
    course = CourseLightSerializer(read_only=True, exclude_abilities=True)
    enrollment = EnrollmentLightSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True, exclude_abilities=True)
    product_title = serializers.SlugRelatedField(
        read_only=True, slug_field="title", source="product"
    )
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = models.Order
        fields = [
            "id",
            "course",
            "enrollment",
            "organization",
            "owner_name",
            "product_title",
            "state",
        ]
        read_only_fields = fields

    def get_owner_name(self, instance) -> str:
        """
        Return the name full name of the order's owner or fallback to username
        """
        return instance.owner.get_full_name() or instance.owner.username


class CertificationDefinitionSerializer(serializers.ModelSerializer):
    """
    Serialize information about a certificate definition
    """

    description = serializers.CharField(read_only=True)

    class Meta:
        model = models.CertificateDefinition
        fields = ["description", "name", "title"]
        read_only_fields = fields


class CertificateSerializer(serializers.ModelSerializer):
    """
    Certificate model serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    certificate_definition = CertificationDefinitionSerializer(read_only=True)
    order = NestedOrderSerializer(read_only=True)
    enrollment = EnrollmentLightSerializer(read_only=True)

    class Meta:
        model = models.Certificate
        fields = [
            "id",
            "certificate_definition",
            "issued_on",
            "order",
            "enrollment",
        ]
        read_only_fields = fields

    def get_context(self, certificate) -> dict:
        """
        Compute the serialized value for the "context" field.
        """
        language = self.context["request"].LANGUAGE_CODE or get_language()
        return certificate.localized_context[language]


class ContractDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for ContractDefinition model serializer"""

    class Meta:
        model = models.ContractDefinition
        fields = ["id", "description", "language", "title"]
        read_only_fields = fields


class ContractLightSerializer(serializers.ModelSerializer):
    """Light serializer for Contract model."""

    class Meta:
        model = models.Contract
        fields = ["id", "organization_signed_on", "student_signed_on"]
        read_only_fields = fields


class ContractSerializer(AbilitiesModelSerializer):
    """Serializer for Contract model serializer"""

    id = serializers.CharField(read_only=True, required=False)
    definition = ContractDefinitionSerializer()
    order = NestedOrderSerializer()
    organization_signatory = UserSerializer(read_only=True)

    class Meta:
        model = models.Contract
        fields = [
            "created_on",
            "definition",
            "id",
            "order",
            "organization_signatory",
            "organization_signed_on",
            "student_signed_on",
        ]
        read_only_fields = fields


class CourseRunLightSerializer(serializers.ModelSerializer):
    """
    Serialize all information about a course run
    """

    class Meta:
        model = models.CourseRun
        fields = [
            "end",
            "enrollment_end",
            "enrollment_start",
            "id",
            "languages",
            "resource_link",
            "start",
            "title",
            "state",
        ]
        read_only_fields = fields


class ProductTargetCourseRelationSerializer(serializers.ModelSerializer):
    """
    Serializer for ProductTargetCourseRelation model
    """

    position = serializers.IntegerField(read_only=True)
    is_graded = serializers.BooleanField(read_only=True)
    course_runs = serializers.SerializerMethodField("get_course_runs")
    title = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()

    class Meta:
        model = models.ProductTargetCourseRelation
        fields = ("code", "course_runs", "is_graded", "position", "title")
        read_only_fields = fields

    def get_course_runs(self, relation) -> list[dict]:
        """Return all course runs for courses targeted by the product."""
        queryset = relation.product.target_course_runs.filter(
            course=relation.course
        ).order_by("start")

        return CourseRunLightSerializer(queryset, many=True).data

    def get_code(self, relation) -> str:
        """Return the code of the targeted course"""
        return relation.course.code

    def get_title(self, relation) -> str:
        """Return the title of the targeted course"""
        return relation.course.title


class OrderTargetCourseRelationSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderTargetCourseRelation model
    """

    position = serializers.IntegerField(read_only=True)
    is_graded = serializers.BooleanField(read_only=True)
    course_runs = serializers.SerializerMethodField("get_course_runs")
    title = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()

    class Meta:
        model = models.OrderTargetCourseRelation
        fields = ("code", "course_runs", "is_graded", "position", "title")
        read_only_fields = fields

    def get_course_runs(self, relation) -> list[dict]:
        """Return all course runs targeted by the order."""
        queryset = relation.order.target_course_runs.filter(
            course=relation.course
        ).order_by("start")

        return CourseRunLightSerializer(queryset, many=True).data

    def get_code(self, relation) -> str:
        """Return the code of the targeted course"""
        return relation.course.code

    def get_title(self, relation) -> str:
        """Return the title of the targeted course"""
        return relation.course.title


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Enrollment model serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    certificate_id = serializers.SlugRelatedField(
        read_only=True, slug_field="id", source="certificate"
    )
    course_run = CourseRunSerializer(read_only=True)
    product_relations = serializers.SerializerMethodField(read_only=True)
    orders = serializers.SerializerMethodField(read_only=True)
    was_created_by_order = serializers.BooleanField(required=True)

    class Meta:
        model = models.Enrollment
        fields = [
            "certificate_id",
            "course_run",
            "created_on",
            "id",
            "is_active",
            "orders",
            "product_relations",
            "state",
            "was_created_by_order",
        ]
        read_only_fields = ["course_run", "created_on", "id", "state"]

    def create(self, validated_data, **kwargs):
        """
        Retrieve the course run resource through the provided id
        then try to create the enrollment resource.
        """

        # Retrieve the course run id from the request body through the course run
        # property. This field is a nested serializer for read only purpose, but to
        # create/update an enrollment, we do not want the frontend has to provide the
        # whole course run resource but only its id. So we retrieve the course run id
        # from request body and use it to retrieve the course run resource.
        try:
            course_run_id = self.initial_data["course_run_id"]
        except KeyError as exception:
            message = "You must provide a course_run_id to create an enrollment."
            raise serializers.ValidationError({"__all__": [message]}) from exception

        try:
            course_run = models.CourseRun.objects.get(id=course_run_id)
        except models.CourseRun.DoesNotExist as exception:
            message = f'A course run with id "{course_run_id}" does not exist.'
            raise serializers.ValidationError({"__all__": [message]}) from exception

        validated_data["course_run"] = course_run

        return super().create(validated_data=validated_data)

    def update(self, instance, validated_data):
        """
        Restrict the values that can be set from the API for the state field to "set".
        The "failed" state can only be set by the LMSHandler. The `was_created_by_order`
        field should be updated only if the enrollment was previously inactive.
        """
        if instance.is_active is True:
            validated_data.pop("was_created_by_order", None)

        return super().update(instance, validated_data)

    def get_product_relations(self, instance) -> list[dict]:
        """
        Get products related to the enrollment's course run.
        """
        if instance.was_created_by_order:
            return []

        # Try getting the related products that may have been annotated on the instance when the
        # call originates from a viewset (the viewset annotates the query to minimize database
        # calls) and default to querying the database ourselves
        try:
            relations = instance.course_run.course.certificate_product_relations
        except AttributeError:
            relations = models.CourseProductRelation.objects.filter(
                product__type=enums.PRODUCT_TYPE_CERTIFICATE,
                course=instance.course_run.course,
            )

        return ProductRelationSerializer(
            relations,
            many=True,
        ).data

    def get_orders(self, instance) -> list[dict]:
        """Get orders pointing to the enrollment."""
        if instance.was_created_by_order:
            return []

        # Try getting the related orders that may have been prefetched on the instance by the
        # viewset (the viewset prefetches related orders to minimize database calls) and default
        # to querying the database ourselves
        try:
            orders = instance.related_orders
        except AttributeError:
            orders = models.Order.objects.filter(enrollment=instance)

        context = self.context.copy()
        context["resource"] = instance

        return OrderLightSerializer(
            orders,
            many=True,
            context=context,
        ).data


class OrderPaymentSerializer(serializers.Serializer):
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


class OrderLightSerializer(serializers.ModelSerializer):
    """Order model light serializer."""

    product_id = serializers.SlugRelatedField(
        queryset=models.Product.objects.all(), slug_field="id", source="product"
    )
    certificate_id = serializers.SlugRelatedField(
        queryset=models.Certificate.objects.all(), slug_field="id", source="certificate"
    )
    payment_schedule = OrderPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = models.Order
        fields = [
            "id",
            "certificate_id",
            "product_id",
            "state",
            "payment_schedule",
        ]
        read_only_fields = fields


class OrderGroupSerializer(serializers.ModelSerializer):
    """Serializer for order groups in a product."""

    nb_available_seats = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.OrderGroup
        fields = ["id", "is_active", "nb_seats", "nb_available_seats"]
        read_only_fields = fields

    def get_nb_available_seats(self, order_group) -> int:
        """Return the number of available seats for this order group."""
        return order_group.nb_seats - order_group.get_nb_binding_orders()


class DefinitionResourcesProductSerializer(serializers.ModelSerializer):
    """
    A serializer for product model which only bind the related
    definition resources.
    """

    certificate_definition_id = serializers.SlugRelatedField(
        read_only=True, source="certificate_definition", slug_field="id"
    )
    contract_definition_id = serializers.SlugRelatedField(
        read_only=True, source="contract_definition", slug_field="id"
    )

    class Meta:
        model = models.Product
        fields = ["id", "contract_definition_id", "certificate_definition_id"]
        read_only_fields = fields


class ProductSerializer(serializers.ModelSerializer):
    """
    Product serializer including
        - certificate definition information if there is
        - contract definition information if there is
        - targeted courses with its course runs
            - If user is authenticated, we try to retrieve enrollment related
              to each course run.
        - order if user is authenticated
    """

    id = serializers.CharField(read_only=True)
    instructions = serializers.SerializerMethodField(read_only=True)
    certificate_definition = CertificationDefinitionSerializer(read_only=True)
    price = serializers.DecimalField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=D(0.00),
        read_only=True,
    )
    price_currency = serializers.SerializerMethodField(read_only=True)
    target_courses = ProductTargetCourseRelationSerializer(
        read_only=True, many=True, source="target_course_relations"
    )
    contract_definition = ContractDefinitionSerializer(read_only=True)

    class Meta:
        model = models.Product
        fields = [
            "call_to_action",
            "certificate_definition",
            "contract_definition",
            "id",
            "instructions",
            "price",
            "price_currency",
            "state",
            "target_courses",
            "title",
            "type",
        ]
        read_only_fields = fields

    def get_price_currency(self, *args, **kwargs) -> str:
        """Return the code of currency used by the instance"""
        return settings.DEFAULT_CURRENCY

    def get_instructions(self, instance) -> str:
        """Return the instruction of the instance in html format."""
        instructions = instance.safe_translation_getter(
            "instructions", any_language=True
        )
        if not instructions:
            return ""

        return markdown.markdown(instructions)


class CourseSerializer(AbilitiesModelSerializer):
    """
    Serialize all non-sensitive course information. This serializer is read only.
    """

    cover = ThumbnailDetailField()
    organizations = OrganizationSerializer(many=True, read_only=True)
    product_ids = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="id", source="products"
    )
    course_run_ids = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="id", source="course_runs"
    )
    effort = ISO8601DurationField()

    class Meta:
        model = models.Course
        fields = [
            "created_on",
            "code",
            "course_run_ids",
            "cover",
            "id",
            "organizations",
            "product_ids",
            "state",
            "title",
            "effort",
        ]
        read_only_fields = fields


class CourseProductRelationSerializer(CachedModelSerializer):
    """
    Serialize a course product relation.
    """

    course = CourseLightSerializer(read_only=True, exclude_abilities=True)
    product = ProductSerializer(read_only=True)
    organizations = OrganizationSerializer(
        many=True, read_only=True, exclude_abilities=True
    )
    order_groups = OrderGroupSerializer(many=True, read_only=True)

    class Meta:
        model = models.CourseProductRelation
        fields = [
            "course",
            "created_on",
            "id",
            "order_groups",
            "organizations",
            "product",
        ]
        read_only_fields = fields


class ProductRelationSerializer(CachedModelSerializer):
    """
    Serialize a course product relation.
    """

    product = ProductSerializer(read_only=True)

    class Meta:
        model = models.CourseProductRelation
        fields = [
            "id",
            "order_groups",
            "product",
        ]
        read_only_fields = fields


class GenerateSignedContractsZipSerializer(serializers.Serializer):
    """
    Serializer used by both view and command generating a zip containing signed contracts
    """

    course_product_relation_id = serializers.UUIDField(allow_null=True, required=False)
    organization_id = serializers.UUIDField(allow_null=True, required=False)

    def validate(self, attrs):
        """
        Validate that course_product_relation_id and organization_id are mutually exclusive
        but at least one is required.

        Also, it fetch in database the corresponding object to add them in the validated data.
        """
        course_product_relation_id = attrs.get("course_product_relation_id")
        organization_id = attrs.get("organization_id")

        if not course_product_relation_id and not organization_id:
            raise serializers.ValidationError(
                "You must set at least one parameter for the method."
                "You must choose between an Organization UUID or a Course Product Relation UUID."
            )

        errors = {}
        if course_product_relation_id:
            try:
                attrs["course_product_relation"] = (
                    models.CourseProductRelation.objects.get(
                        pk=course_product_relation_id
                    )
                )
            except models.CourseProductRelation.DoesNotExist:
                errors["course_product_relation_id"] = (
                    "Make sure to give an existing course product relation UUID. "
                    "No CourseProductRelation was found with the given "
                    f"UUID : {attrs.get('course_product_relation_id')}."
                )

        if organization_id:
            try:
                attrs["organization"] = models.Organization.objects.get(
                    pk=organization_id
                )
            except models.Organization.DoesNotExist:
                errors["organization_id"] = (
                    "Make sure to give an existing organization UUID. "
                    "No Organization was found with the given UUID : "
                    f"{attrs.get('organization_id')}."
                )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class UserLightSerializer(serializers.ModelSerializer):
    """Light serializer for User model."""

    full_name = serializers.CharField(source="get_full_name")

    class Meta:
        model = models.User
        fields = ["id", "username", "full_name", "email"]
        read_only_fields = fields


class NestedOrderCourseSerializer(serializers.ModelSerializer):
    """
    Serializer for orders made on courses.
    """

    id = serializers.CharField(read_only=True)
    organization = OrganizationSerializer(read_only=True, exclude_abilities=True)
    owner = UserLightSerializer(read_only=True)
    product = DefinitionResourcesProductSerializer(read_only=True)
    contract = ContractLightSerializer(read_only=True)
    course_id = serializers.SlugRelatedField(
        read_only=True, slug_field="id", source="course"
    )
    enrollment_id = serializers.SlugRelatedField(
        read_only=True, slug_field="id", source="enrollment"
    )
    certificate_id = serializers.SlugRelatedField(
        read_only=True, slug_field="id", source="certificate"
    )

    class Meta:
        model = models.Order
        fields = [
            "certificate_id",
            "contract",
            "course_id",
            "created_on",
            "enrollment_id",
            "id",
            "organization",
            "owner",
            "product",
            "state",
        ]
        read_only_fields = fields


class ActivityLogContextSerializer(serializers.Serializer):
    """
    Serializer for the context field of the ActivityLog model
    """

    order_id = serializers.UUIDField(
        required=False, help_text="Order of the failed payment"
    )

    def to_internal_value(self, data):
        if "order_id" in data:
            data["order_id"] = str(data["order_id"])
        return data

    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):
        return validated_data


class ActivityLogSerializer(serializers.ModelSerializer):
    """
    Serializer for ActivityLog model
    """

    user_id = serializers.SlugRelatedField(
        queryset=models.User.objects.all(),
        slug_field="id",
        source="user",
        required=True,
    )
    created_on = serializers.DateTimeField(read_only=True)
    context = ActivityLogContextSerializer(required=False)
    level = serializers.ChoiceField(
        required=False,
        choices=models.ActivityLog._meta.get_field("level").choices,
        default=models.ActivityLog._meta.get_field("level").default,
    )
    type = serializers.ChoiceField(
        required=False,
        choices=models.ActivityLog._meta.get_field("type").choices,
        default=models.ActivityLog._meta.get_field("type").default,
    )

    class Meta:
        model = models.ActivityLog
        fields = [
            "id",
            "user_id",
            "level",
            "created_on",
            "type",
            "context",
        ]
        read_only_fields = ["id", "created_on"]


class OrderPaymentScheduleSerializer(serializers.Serializer):
    """
    Serializer for the order payment schedule
    """

    payment_schedule = OrderPaymentSerializer(many=True, required=True)

    def create(self, validated_data):
        """Only there to avoid a NotImplementedError"""

    def update(self, instance, validated_data):
        """Only there to avoid a NotImplementedError"""


class OrderSerializer(serializers.ModelSerializer):
    """
    Order model serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    owner = serializers.CharField(
        source="owner.username", read_only=True, required=False
    )
    course = CourseLightSerializer(
        read_only=True, exclude_abilities=True, required=False
    )
    enrollment = EnrollmentLightSerializer(read_only=True, required=False)
    total = serializers.DecimalField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=D(0.00),
        read_only=True,
        required=False,
    )
    total_currency = serializers.SerializerMethodField(read_only=True)
    organization = OrganizationSerializer(read_only=True, exclude_abilities=True)
    product_id = serializers.SlugRelatedField(
        slug_field="id", source="product", read_only=True
    )
    target_enrollments = serializers.SerializerMethodField(read_only=True)
    order_group_id = serializers.SlugRelatedField(
        read_only=True,
        slug_field="id",
        required=False,
        source="order_group",
    )
    target_courses = OrderTargetCourseRelationSerializer(
        read_only=True, many=True, source="course_relations"
    )
    main_invoice_reference = serializers.SlugRelatedField(
        read_only=True, slug_field="reference", source="main_invoice"
    )
    certificate_id = serializers.SlugRelatedField(
        read_only=True, slug_field="id", source="certificate"
    )
    contract = ContractSerializer(read_only=True, exclude_abilities=True)
    payment_schedule = OrderPaymentSerializer(many=True, read_only=True)
    credit_card_id = serializers.SlugRelatedField(
        queryset=CreditCard.objects.all(),
        slug_field="id",
        source="credit_card",
        required=False,
    )

    class Meta:
        model = models.Order
        fields = [
            "certificate_id",
            "contract",
            "course",
            "created_on",
            "credit_card_id",
            "enrollment",
            "id",
            "main_invoice_reference",
            "order_group_id",
            "organization",
            "owner",
            "product_id",
            "state",
            "target_courses",
            "target_enrollments",
            "total",
            "total_currency",
            "payment_schedule",
        ]
        read_only_fields = fields

    def get_target_enrollments(self, order) -> list[dict]:
        """
        For the current order, retrieve its related enrollments if the order is linked
        to a course.
        """
        if order.enrollment:
            return []

        return EnrollmentSerializer(
            instance=order.get_target_enrollments(),
            many=True,
            context=self.context,
        ).data

    def create(self, validated_data):
        """
        Create a new order and set the organization if provided.
        """
        organization_id = self.initial_data.get("organization_id")

        if organization_id:
            organization = get_object_or_404(models.Organization, id=organization_id)
            validated_data["organization"] = organization

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Make the "course", "organization", "order_group" and "product" fields read_only
        only on update.
        """
        validated_data.pop("course", None)
        validated_data.pop("enrollment", None)
        validated_data.pop("organization", None)
        validated_data.pop("product", None)
        validated_data.pop("order_group", None)
        return super().update(instance, validated_data)

    def get_total_currency(self, *args, **kwargs) -> str:
        """
        Return the currency used
        """
        return settings.DEFAULT_CURRENCY
