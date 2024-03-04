# pylint: disable=too-many-lines
"""Admin serializers for Joanie Core app."""

from django.conf import settings

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from joanie.core import models
from joanie.core.enums import ALL_LANGUAGES
from joanie.core.serializers.fields import (
    ImageDetailField,
    ISO8601DurationField,
    ThumbnailDetailField,
)
from joanie.payment import models as payment_models


class AdminContractDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for ContractDefinition model."""

    title = serializers.CharField()

    class Meta:
        model = models.ContractDefinition
        fields = ("id", "body", "description", "language", "title", "name")
        read_only_fields = ["id"]


class AdminCertificateDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for CertificationDefinition model."""

    title = serializers.CharField()
    description = serializers.CharField(required=False)

    class Meta:
        model = models.CertificateDefinition
        fields = ("id", "name", "title", "description", "template")
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
    languages = serializers.MultipleChoiceField(choices=ALL_LANGUAGES)

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
        Update the address object if the relation exists between the address and the
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
                            "The relation does not exist between the address and the organization."
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
        coerce_to_string=False, decimal_places=2, max_digits=9, min_value=0
    )
    price_currency = serializers.SerializerMethodField(read_only=True)
    instructions = serializers.CharField(
        allow_blank=True, trim_whitespace=False, required=False
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
        ]
        read_only_fields = ["id"]

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
        min_value=0,
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


class AdminOrderGroupSerializer(serializers.ModelSerializer):
    """
    Admin Serializer for OrderGroup model
    """

    nb_available_seats = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.OrderGroup
        fields = [
            "id",
            "nb_seats",
            "is_active",
            "nb_available_seats",
            "created_on",
            "can_edit",
        ]
        read_only_fields = ["id", "can_edit", "created_on"]

    def get_nb_available_seats(self, order_group) -> int:
        """Return the number of available seats for this order group."""
        return order_group.nb_seats - order_group.get_nb_binding_orders()


@extend_schema_serializer(exclude_fields=("course_product_relation",))
class AdminOrderGroupCreateSerializer(AdminOrderGroupSerializer):
    """
    Admin Serializer for OrderGroup model reserved to create action.

    Unlike `AdminOrderGroupSerializer`, it allows to pass a product to create
    the order group.
    """

    class Meta(AdminOrderGroupSerializer.Meta):
        fields = [*AdminOrderGroupSerializer.Meta.fields, "course_product_relation"]


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


class AdminCourseProductRelationsSerializer(serializers.ModelSerializer):
    """
    Serialize all information about a course relation nested in a product.
    """

    course = AdminCourseNestedSerializer(read_only=True)
    product = AdminProductSerializer(read_only=True)
    organizations = AdminOrganizationLightSerializer(many=True, read_only=True)
    order_groups = AdminOrderGroupSerializer(many=True, read_only=True)

    class Meta:
        model = models.CourseProductRelation
        fields = [
            "id",
            "can_edit",
            "course",
            "organizations",
            "order_groups",
            "product",
            "uri",
        ]
        read_only_fields = ["id", "can_edit", "order_groups", "uri"]

    def create(self, validated_data):
        """
        Create a new course relation and attach provided organizations to it
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


class AdminCourseRelationsSerializer(AdminCourseProductRelationsSerializer):
    """
    Serialize all information about a course relation nested in a product.
    """

    class Meta(AdminCourseProductRelationsSerializer.Meta):
        fields = [
            field
            for field in AdminCourseProductRelationsSerializer.Meta.fields
            if field != "product"
        ]
        read_only_fields = fields


class AdminProductRelationSerializer(AdminCourseProductRelationsSerializer):
    """Serializer for CourseProductRelation model."""

    class Meta(AdminCourseProductRelationsSerializer.Meta):
        fields = [
            field
            for field in AdminCourseProductRelationsSerializer.Meta.fields
            if field != "course"
        ]
        read_only_fields = ["id", "can_edit", "order_groups"]


class AdminCourseAccessSerializer(serializers.ModelSerializer):
    """Serializer for CourseAccess model."""

    user = AdminUserSerializer(read_only=True)

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
    product_relations = AdminProductRelationSerializer(many=True, read_only=True)
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
            "product_relations",
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
            "product_relations",
        )

    def validate(self, attrs):
        """
        Validate that the course has at least one organization provided then pass
        the list of organization ids from initial_data to validated_data until
        serializer instance accepts partial data.
        """
        validated_data = super().validate(attrs)
        validated_data["organizations"] = self.initial_data.get("organization_ids", [])
        product_relations = self.initial_data.get("product_relations")

        if product_relations is not None:
            validated_data["product_relations"] = []
            products = models.Product.objects.filter(
                id__in=[p["product_id"] for p in product_relations]
            )
            for product in products:
                relation = next(
                    (
                        p
                        for p in product_relations
                        if p["product_id"] == str(product.id)
                    ),
                    None,
                )
                if relation is not None:
                    relation["product"] = product
                    validated_data["product_relations"].append(relation)

        if self.partial is False and len(validated_data["organizations"]) == 0:
            raise serializers.ValidationError("Organizations are required.")

        return validated_data

    def create(self, validated_data):
        """
        Create a new course and attach provided organizations to it
        """
        organization_ids = validated_data.pop("organizations")
        product_relations = validated_data.pop("product_relations", [])
        course = super().create(validated_data)
        course.organizations.set(organization_ids)

        if len(product_relations) > 0:
            for product_relation in product_relations:
                relation = course.product_relations.create(
                    product=product_relation["product"]
                )
                relation.organizations.set(product_relation["organization_ids"])

        return course

    def update(self, instance, validated_data):
        """
        Attach provided organizations to the course instance then update it.
        """
        if len(validated_data.get("organizations")) == 0:
            organizations_ids = validated_data.pop("organizations")
            instance.organizations.set(organizations_ids)

        if validated_data.get("product_relations") is not None:
            product_relations = validated_data.pop("product_relations")
            if len(product_relations) == 0:
                instance.product_relations.all().delete()

            else:
                for product_relation in product_relations:
                    (relation, _) = instance.product_relations.get_or_create(
                        product=product_relation["product"]
                    )
                    relation.organizations.set(product_relation["organization_ids"])

        return super().update(instance, validated_data)


class AdminCourseRunSerializer(serializers.ModelSerializer):
    """Serializer for CourseRun model."""

    title = serializers.CharField()
    course = AdminCourseLightSerializer(read_only=True)
    languages = serializers.MultipleChoiceField(choices=ALL_LANGUAGES)

    class Meta:
        model = models.CourseRun
        fields = [
            "id",
            "course",
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
        Return the relevant target course relation depending on whether the resource context
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
        Retrieve the position of the course related to its product/order relation
        """
        relation = self.get_target_course_relation(target_course)

        return relation.position

    def get_is_graded(self, target_course):
        """
        Retrieve the `is_graded` state of the course related to its product/order relation
        """
        relation = self.get_target_course_relation(target_course)

        return relation.is_graded

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


class AdminProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for Product details"""

    certificate_definition = AdminCertificateDefinitionSerializer(read_only=True)
    contract_definition = AdminContractDefinitionSerializer(read_only=True)
    target_courses = serializers.SerializerMethodField(read_only=True)
    price = serializers.DecimalField(
        coerce_to_string=False, decimal_places=2, max_digits=9, min_value=0
    )
    course_relations = AdminCourseRelationsSerializer(read_only=True, many=True)
    price_currency = serializers.SerializerMethodField(read_only=True)

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
            "course_relations",
            "instructions",
        ]
        read_only_fields = fields

    def get_target_courses(self, product):
        """Compute the serialized value for the "target_courses" field."""
        context = self.context.copy()
        context["resource"] = product

        relations = models.ProductTargetCourseRelation.objects.filter(
            product=product
        ).order_by("position")

        return AdminProductTargetCourseRelationNestedSerializer(
            instance=relations, many=True, context=context
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


class AdminOrderSerializer(serializers.ModelSerializer):
    """Read only Serializer for Order model."""

    product = AdminProductLightSerializer(read_only=True)
    course = AdminCourseLightSerializer(read_only=True)
    enrollment = AdminOrderEnrollmentSerializer(read_only=True)
    owner = AdminUserSerializer(read_only=True)
    total = serializers.DecimalField(
        coerce_to_string=False, decimal_places=2, max_digits=9, min_value=0
    )
    total_currency = serializers.SerializerMethodField(read_only=True)
    contract = AdminContractSerializer()
    certificate = AdminCertificateSerializer()
    main_invoice = AdminInvoiceSerializer()
    organization = AdminOrganizationLightSerializer(read_only=True)
    order_group = AdminOrderGroupSerializer(read_only=True)

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
            "order_group",
            "total",
            "total_currency",
            "contract",
            "certificate",
            "main_invoice",
            "has_consent_to_terms",
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
        coerce_to_string=False, decimal_places=2, max_digits=9, min_value=0
    )
    total_currency = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Order
        fields = (
            "course_code",
            "created_on",
            "enrollment_id",
            "id",
            "organization_title",
            "owner_name",
            "product_title",
            "state",
            "total",
            "total_currency",
        )
        read_only_fields = fields

    def get_total_currency(self, *args, **kwargs) -> str:
        """Return the code of currency used by the instance"""
        return settings.DEFAULT_CURRENCY

    def get_owner_name(self, instance) -> str:
        """
        Return the full name of the order's owner if available,
        otherwise fallback to the username
        """
        return instance.owner.get_full_name() or instance.owner.username
