"""Admin serializers for Joanie Core app."""
from django.conf import settings

from djmoney.contrib.django_rest_framework import MoneyField
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from joanie.core import models
from joanie.core.enums import ALL_LANGUAGES
from joanie.core.serializers.fields import ImageDetailField, ThumbnailDetailField


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


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    full_name = serializers.CharField(source="get_full_name")

    class Meta:
        model = models.User
        fields = ["id", "username", "full_name"]
        read_only_fields = ["id", "username", "full_name"]


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
        user_id = self.initial_data.get("user")
        if user_id is not None:
            try:
                validated_data["user"] = models.User.objects.get(id=user_id)
            except models.User.DoesNotExist as exception:
                raise serializers.ValidationError(
                    {"user": "Resource does not exist."}
                ) from exception
        elif self.partial is False and user_id is None:
            raise serializers.ValidationError({"user": "This field is required."})

        return validated_data


class AdminOrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model."""

    title = serializers.CharField()
    logo = ThumbnailDetailField(required=False)
    signature = ImageDetailField(required=False)
    accesses = AdminOrganizationAccessSerializer(many=True, read_only=True)

    class Meta:
        model = models.Organization
        fields = (
            "accesses",
            "code",
            "id",
            "logo",
            "representative",
            "signature",
            "title",
        )
        read_only_fields = (
            "accesses",
            "id",
        )


class AdminOrganizationLightSerializer(serializers.ModelSerializer):
    """Read-only light Serializer for Organization model."""

    class Meta:
        model = models.Organization
        fields = ("code", "title", "id")
        read_only_fields = ("code", "title", "id")


class AdminProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model."""

    title = serializers.CharField()
    description = serializers.CharField(required=False)
    call_to_action = serializers.CharField()
    price = MoneyField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=0,
    )
    price_currency = serializers.ChoiceField(choices=settings.CURRENCIES)

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
            "target_courses",
        ]
        read_only_fields = ["id"]


class AdminProductRelationSerializer(serializers.ModelSerializer):
    """Serializer for CourseProductRelation model."""

    organizations = AdminOrganizationLightSerializer(many=True)
    product = AdminProductSerializer()

    class Meta:
        model = models.CourseProductRelation
        fields = (
            "id",
            "product",
            "organizations",
        )
        read_only_fields = ["id"]


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
        user_id = self.initial_data.get("user")
        if user_id is not None:
            try:
                validated_data["user"] = models.User.objects.get(id=user_id)
            except models.User.DoesNotExist as exception:
                raise serializers.ValidationError(
                    {"user": "Resource does not exist."}
                ) from exception
        elif self.partial is False and user_id is None:
            raise serializers.ValidationError({"user": "This field is required."})

        return validated_data


class AdminCourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model."""

    title = serializers.CharField()
    cover = ThumbnailDetailField(required=False)
    organizations = AdminOrganizationLightSerializer(many=True, read_only=True)
    product_relations = AdminProductRelationSerializer(many=True, read_only=True)
    accesses = AdminCourseAccessSerializer(many=True, read_only=True)

    class Meta:
        model = models.Course
        fields = (
            "accesses",
            "code",
            "cover",
            "id",
            "organizations",
            "product_relations",
            "state",
            "title",
        )
        read_only_fields = (
            "accesses",
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
        validated_data["organizations"] = self.initial_data.get("organizations", [])
        product_relations = self.initial_data.get("product_relations")

        if product_relations is not None:
            validated_data["product_relations"] = []
            products = models.Product.objects.filter(
                id__in=[p["product"] for p in product_relations]
            )
            for product in products:
                relation = next(
                    (p for p in product_relations if p["product"] == str(product.id)),
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
                relation.organizations.set(product_relation["organizations"])

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
                    relation.organizations.set(product_relation["organizations"])

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
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        """
        Validate that the course run has a course provided then bind the course instance
        to validated_data until serializer instance accepts partial data.
        """
        validated_data = super().validate(attrs)
        course_id = self.initial_data.get("course", None)

        if self.partial is False and course_id is None:
            raise serializers.ValidationError({"course": "This field cannot be null."})

        if course_id:
            try:
                validated_data["course"] = models.Course.objects.get(id=course_id)
            except models.Course.DoesNotExist as exception:
                raise serializers.ValidationError(
                    {"course": "Resource {course_id} does not exist."}, exception
                )

        return validated_data
