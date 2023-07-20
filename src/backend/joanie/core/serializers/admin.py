"""Admin serializers for Joanie Core app."""
from django.conf import settings

from djmoney.contrib.django_rest_framework import MoneyField
from rest_framework import serializers

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
        fields = ("code", "title", "id")
        read_only_fields = ("code", "title", "id")


class AdminOrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model."""

    title = serializers.CharField()
    logo = ThumbnailDetailField(required=False)
    signature = ImageDetailField(required=False)

    class Meta:
        model = models.Organization
        fields = ["id", "code", "title", "representative", "signature", "logo"]
        read_only_fields = ["id"]


class AdminOrganizationLightSerializer(serializers.ModelSerializer):
    """Read-only light Serializer for Organization model."""

    class Meta:
        model = models.Organization
        fields = ["code", "title", "id"]
        read_only_fields = ["code", "title", "id"]


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
        read_only_fields = [
            "id",
        ]

    def to_representation(self, instance):
        serializer = AdminProductDetailSerializer(instance)
        return serializer.data

    def add_target_courses(self, product, target_courses_data):
        """
        Create or update target course and add it to the list of target courses
        associated to the product
        """

        product.target_courses.clear()
        for target_course_data in target_courses_data:
            if "id" in target_course_data:
                instance = models.Course.objects.get(id=target_course_data.pop("id"))
                course_serializer = AdminCourseSerializer(
                    instance=instance, data=target_course_data
                )
                course_serializer.is_valid(raise_exception=True)
                course = course_serializer.update(
                    instance=instance, validated_data=course_serializer.validated_data
                )
            else:
                course_serializer = AdminCourseSerializer(data=target_course_data)
                course_serializer.is_valid(raise_exception=True)
                course = course_serializer.create(
                    validated_data=course_serializer.validated_data
                )
            product.target_courses.add(course)

    def add_course_relations(self, product, course_relations_data):
        """
        Create and link CourseProductRelation to the product
        """
        models.CourseProductRelation.objects.filter(product__id=product.id).delete()
        for course_relation_data in course_relations_data:
            course_id = course_relation_data.pop("course", "")
            course_relation = models.CourseProductRelation.objects.create(
                product=product, course=models.Course.objects.get(id=course_id)
            )
            organization_ids = course_relation_data.pop("organizations", [])
            for organization_id in organization_ids:
                course_relation.organizations.add(organization_id)

    def create(self, validated_data):
        product = super().create(validated_data)
        if "target_courses" in self.initial_data:
            target_courses_data = self.initial_data.pop("target_courses")
            self.add_target_courses(product, target_courses_data)
        if "course_relations" in self.initial_data:
            course_relations_data = self.initial_data.pop("course_relations")
            self.add_course_relations(product, course_relations_data)
        return product

    def update(self, instance, validated_data):
        product = super().update(instance, validated_data)
        if "target_courses" in self.initial_data:
            target_courses_data = self.initial_data.pop("target_courses")
            product.target_courses.clear()
            self.add_target_courses(product, target_courses_data)
        if "course_relations" in self.initial_data:
            course_relations_data = self.initial_data.pop("course_relations")
            self.add_course_relations(product, course_relations_data)
        return product


class AdminProductListSerializer(serializers.ModelSerializer):
    """Serializer for listing Product model."""

    class Meta:
        model = models.Product
        fields = [
            "id",
            "title",
            "price",
            "price_currency",
            "type",
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


class AdminCourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model."""

    title = serializers.CharField()
    cover = ThumbnailDetailField(required=False)
    organizations = AdminOrganizationLightSerializer(many=True, read_only=True)
    product_relations = AdminProductRelationSerializer(many=True, read_only=True)

    class Meta:
        model = models.Course
        fields = (
            "id",
            "code",
            "cover",
            "title",
            "organizations",
            "product_relations",
            "state",
        )
        read_only_fields = ["id", "state"]

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


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    full_name = serializers.CharField(source="get_full_name")

    class Meta:
        model = models.User
        fields = ["username", "full_name"]
        read_only_fields = ["username", "full_name"]


class AdminCourseRelationForProductSerializer(serializers.ModelSerializer):
    """Serializer for CourseProductRelation model."""

    class Meta:
        model = models.CourseProductRelation
        fields = (
            "id",
            "organizations",
        )
        read_only_fields = ["id"]


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

    def get_course_runs(self, target_course):
        """
        Return related course runs ordered by start date asc
        """
        course_runs = self.context_resource.target_course_runs.filter(
            course=target_course
        ).order_by("start")

        return AdminCourseRunSerializer(course_runs, many=True).data


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


class AdminCourseRelationsSerializer(serializers.ModelSerializer):
    """
    Serialize all information about a course relation nested in a product.
    """

    course = AdminCourseNestedSerializer(read_only=True)
    organizations = AdminOrganizationLightSerializer(many=True, read_only=True)

    class Meta:
        model = models.CourseProductRelation
        fields = [
            "id",
            "course",
            "organizations",
        ]
        read_only_fields = [
            "id",
            "course",
            "organizations",
        ]


class AdminProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for Product details"""

    certificate_definition = AdminCertificateDefinitionSerializer()
    target_courses = serializers.SerializerMethodField(read_only=True)
    price = MoneyField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=0,
    )
    course_relations = AdminCourseRelationsSerializer(read_only=True, many=True)

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
            "target_courses",
            "course_relations",
        ]
        read_only_fields = [
            "id",
            "title",
            "description",
            "call_to_action",
            "type",
            "price",
            "price_currency",
            "certificate_definition",
            "target_courses",
            "course_relations",
        ]

    def get_target_courses(self, product):
        """Compute the serialized value for the "target_courses" field."""
        context = self.context.copy()
        context["resource"] = product

        return AdminTargetCourseSerializer(
            instance=product.target_courses.all().order_by("order_relations__position"),
            many=True,
            context=context,
        ).data
