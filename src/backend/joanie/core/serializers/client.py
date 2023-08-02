"""Client serializers for Joanie Core app."""
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions, serializers

from joanie.core import enums, models, utils
from joanie.core.serializers.fields import ThumbnailDetailField


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


class AddressSerializer(serializers.ModelSerializer):
    """
    Address model serializer
    """

    id = serializers.CharField(read_only=True, required=False)

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
        read_only_fields = [
            "code",
            "cover",
            "id",
            "title",
        ]


class CourseAccessSerializer(AbilitiesModelSerializer):
    """Serialize course accesses for the API."""

    class Meta:
        model = models.CourseAccess
        fields = ["id", "role", "user"]
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

    logo = ThumbnailDetailField(required=False)

    class Meta:
        model = models.Organization
        fields = ["id", "code", "logo", "title"]
        read_only_fields = ["id", "code", "logo", "title"]


class OrganizationAccessSerializer(AbilitiesModelSerializer):
    """Serialize Organization accesses for the API."""

    class Meta:
        model = models.OrganizationAccess
        fields = ["id", "role", "user"]
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


class CertificateOrderSerializer(serializers.ModelSerializer):
    """
    Order model serializer for the Certificate model
    """

    id = serializers.CharField(read_only=True, required=False)
    course = CourseLightSerializer(read_only=True, exclude_abilities=True)
    organization = OrganizationSerializer(read_only=True, exclude_abilities=True)

    class Meta:
        model = models.Order
        fields = ["id", "course", "organization"]
        read_only_fields = ["id", "course", "organization"]


class CertificationDefinitionSerializer(serializers.ModelSerializer):
    """
    Serialize information about a certificate definition
    """

    description = serializers.CharField(read_only=True)

    class Meta:
        model = models.CertificateDefinition
        fields = ["description", "name", "title"]
        read_only_fields = ("description", "name", "title")


class CertificateSerializer(serializers.ModelSerializer):
    """
    Certificate model serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    certificate_definition = CertificationDefinitionSerializer(read_only=True)
    order = CertificateOrderSerializer(read_only=True)

    class Meta:
        model = models.Certificate
        fields = ["id", "certificate_definition", "issued_on", "order"]
        read_only_fields = ["id", "certificate_definition", "issued_on", "order"]

    def get_context(self, certificate):
        """
        Compute the serialized value for the "context" field.
        """
        language = self.context["request"].LANGUAGE_CODE or get_language()
        return certificate.localized_context[language]


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
            "resource_link",
            "start",
            "title",
            "state",
        ]
        read_only_fields = [
            "course",
            "end",
            "enrollment_end",
            "enrollment_start",
            "id",
            "resource_link",
            "start",
            "title",
            "state",
        ]


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
            "resource_link",
            "start",
            "title",
            "state",
        ]
        read_only_fields = [
            "end",
            "enrollment_end",
            "enrollment_start",
            "id",
            "resource_link",
            "start",
            "title",
            "state",
        ]


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

    def get_course_runs(self, relation):
        """Return all course runs for courses targeted by the product."""
        queryset = relation.product.target_course_runs.filter(
            course=relation.course
        ).order_by("start")

        return CourseRunLightSerializer(queryset, many=True).data

    def get_code(self, relation):
        """Return the code of the targeted course"""
        return relation.course.code

    def get_title(self, relation):
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

    def get_course_runs(self, relation):
        """Return all course runs targeted by the order."""
        queryset = relation.order.target_course_runs.filter(
            course=relation.course
        ).order_by("start")

        return CourseRunLightSerializer(queryset, many=True).data

    def get_code(self, relation):
        """Return the code of the targeted course"""
        return relation.course.code

    def get_title(self, relation):
        """Return the title of the targeted course"""
        return relation.course.title


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Enrollment model serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    certificate = serializers.SlugRelatedField(read_only=True, slug_field="id")
    course_run = CourseRunSerializer(read_only=True)
    products = serializers.SerializerMethodField(read_only=True)
    was_created_by_order = serializers.BooleanField(required=True)

    class Meta:
        model = models.Enrollment
        fields = [
            "id",
            "course_run",
            "created_on",
            "is_active",
            "products",
            "state",
            "was_created_by_order",
        ]
        read_only_fields = ["id", "course_run", "created_on", "state"]

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
        course_run_id = self.initial_data["course_run"]

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

    def get_products(self, instance):
        """
        Get products related to the enrollment's course run.
        """
        if instance.was_created_by_order:
            return []

        # Try getting the related products annotated on the instance by the calling
        # viewset and default to querying the database ourselves
        try:
            relations = instance.course_run.course.certificate_product_relations
        except AttributeError:
            products = models.Product.objects.filter(
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                course_relations__course=instance.course_run.course,
            )
        else:
            products = [relation.product for relation in relations]

        context = self.context.copy()
        context.update(
            {
                "resource": instance,
                "course_code": instance.course_run.course.code,
            }
        )

        return ProductSerializer(
            products,
            many=True,
            context=context,
        ).data


class OrderSerializer(serializers.ModelSerializer):
    """
    Order model serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    owner = serializers.CharField(
        source="owner.username", read_only=True, required=False
    )
    course = CourseLightSerializer(read_only=True, exclude_abilities=True)
    total = serializers.DecimalField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=0,
        read_only=True,
        required=False,
    )
    total_currency = serializers.SerializerMethodField(read_only=True)
    organization = serializers.SlugRelatedField(
        queryset=models.Organization.objects.all(), slug_field="id", required=False
    )
    product = serializers.SlugRelatedField(
        queryset=models.Product.objects.all(), slug_field="id"
    )
    enrollments = serializers.SerializerMethodField(read_only=True)
    target_courses = OrderTargetCourseRelationSerializer(
        read_only=True, many=True, source="course_relations"
    )
    main_invoice = serializers.SlugRelatedField(read_only=True, slug_field="reference")
    certificate = serializers.SlugRelatedField(read_only=True, slug_field="id")

    class Meta:
        model = models.Order
        fields = [
            "certificate",
            "course",
            "created_on",
            "enrollments",
            "id",
            "main_invoice",
            "organization",
            "owner",
            "product",
            "state",
            "target_courses",
            "total",
            "total_currency",
        ]
        read_only_fields = [
            "certificate",
            "created_on",
            "course",
            "enrollments",
            "id",
            "main_invoice",
            "owner",
            "state",
            "target_courses",
            "total",
            "total_currency",
        ]

    def get_enrollments(self, order):
        """
        For the current order, retrieve its related enrollments.
        """
        return EnrollmentSerializer(
            instance=order.get_enrollments(),
            many=True,
            context=self.context,
        ).data

    def update(self, instance, validated_data):
        """
        Make the "course", "organization" and "product" fields read_only
        only on update.
        """
        validated_data.pop("course", None)
        validated_data.pop("organization", None)
        validated_data.pop("product", None)
        return super().update(instance, validated_data)

    def get_total_currency(self, *args, **kwargs):
        """
        Return the currency used
        """
        return settings.DEFAULT_CURRENCY


class ProductSerializer(serializers.ModelSerializer):
    """
    Product serializer including
        - certificate information if there is
        - targeted courses with its course runs
            - If user is authenticated, we try to retrieve enrollment related
              to each course run.
        - order if user is authenticated
    """

    id = serializers.CharField(read_only=True)
    certificate_definition = CertificationDefinitionSerializer(read_only=True)
    price = serializers.DecimalField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=0,
        read_only=True,
    )
    price_currency = serializers.SerializerMethodField(read_only=True)
    target_courses = ProductTargetCourseRelationSerializer(
        read_only=True, many=True, source="target_course_relations"
    )

    class Meta:
        model = models.Product
        fields = [
            "call_to_action",
            "certificate_definition",
            "id",
            "price",
            "price_currency",
            "state",
            "target_courses",
            "title",
            "type",
        ]
        read_only_fields = [
            "call_to_action",
            "certificate_definition",
            "id",
            "price",
            "price_currency",
            "state",
            "target_courses",
            "title",
            "type",
        ]

    def to_representation(self, instance):
        """
        Cache the serializer representation for the current instance.
        """
        cache_key = utils.get_resource_cache_key(
            "product_for_course",
            f"{instance.id!s}-{self.context.get('course_code', 'nocourse'):s}",
            is_language_sensitive=True,
        )
        representation = cache.get(cache_key)

        if representation is None:
            representation = super().to_representation(instance)
            cache.set(
                cache_key,
                representation,
                settings.JOANIE_ANONYMOUS_SERIALIZER_DEFAULT_CACHE_TTL,
            )

        return representation

    def get_price_currency(self, *args, **kwargs):
        """Return the code of currency used by the instance"""
        return settings.DEFAULT_CURRENCY


class CourseSerializer(AbilitiesModelSerializer):
    """
    Serialize all non-sensitive course information. This serializer is read only.
    """

    cover = ThumbnailDetailField()
    organizations = OrganizationSerializer(many=True, read_only=True)
    products = serializers.SlugRelatedField(many=True, read_only=True, slug_field="id")
    course_runs = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="id"
    )

    class Meta:
        model = models.Course
        fields = [
            "created_on",
            "code",
            "course_runs",
            "cover",
            "id",
            "organizations",
            "products",
            "state",
            "title",
        ]
        read_only_fields = [
            "created_on",
            "code",
            "course_runs",
            "cover",
            "id",
            "organizations",
            "products",
            "state",
            "title",
        ]


class CourseProductRelationSerializer(serializers.ModelSerializer):
    """
    Serialize a course product relation.
    """

    course = CourseLightSerializer(read_only=True, exclude_abilities=True)
    product = ProductSerializer(read_only=True)
    organizations = OrganizationSerializer(
        many=True, read_only=True, exclude_abilities=True
    )

    class Meta:
        model = models.CourseProductRelation
        fields = [
            "course",
            "created_on",
            "id",
            "organizations",
            "product",
        ]
        read_only_fields = [
            "course",
            "created_on",
            "id",
            "organizations",
            "product",
        ]


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
        read_only_fields = [
            "id",
            "username",
            "full_name",
            "is_superuser",
            "is_staff",
            "abilities",
        ]

    def get_abilities(self, user):
        """Return abilities of the logged-in user on itself."""
        request = self.context.get("request")
        if request:
            return request.user.get_abilities(user)
        return {}
