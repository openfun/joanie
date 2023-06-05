"""Client serializers for Joanie Core app."""

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from djmoney.contrib.django_rest_framework import MoneyField
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


class TargetCourseSerializer(serializers.ModelSerializer):
    """
    Serialize all information about a target course.
    """

    course_runs = serializers.SerializerMethodField(read_only=True)
    organizations = OrganizationSerializer(
        many=True, read_only=True, exclude_abilities=True
    )
    position = serializers.SerializerMethodField(read_only=True)
    is_graded = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Course
        fields = [
            "code",
            "course_runs",
            "is_graded",
            "organizations",
            "position",
            "title",
        ]
        read_only_fields = [
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

        return CourseRunSerializer(course_runs, many=True).data


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Enrollment model serializer
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


class OrderSerializer(serializers.ModelSerializer):
    """
    Order model serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    owner = serializers.CharField(
        source="owner.username", read_only=True, required=False
    )
    course = CourseLightSerializer(read_only=True, exclude_abilities=True)
    total = MoneyField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=0,
        read_only=True,
        required=False,
    )
    organization = serializers.SlugRelatedField(
        queryset=models.Organization.objects.all(), slug_field="id", required=False
    )
    product = serializers.SlugRelatedField(
        queryset=models.Product.objects.all(), slug_field="id"
    )
    enrollments = serializers.SerializerMethodField(read_only=True)
    target_courses = serializers.SerializerMethodField(read_only=True)
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

    def get_target_courses(self, order):
        """Compute the serialized value for the "target_courses" field."""
        context = self.context.copy()
        context["resource"] = order

        return TargetCourseSerializer(
            instance=order.target_courses.all().order_by("order_relations__position"),
            many=True,
            context=context,
        ).data

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
    organizations = serializers.SerializerMethodField("get_organizations")
    price = MoneyField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=0,
        read_only=True,
    )
    target_courses = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Product
        fields = [
            "call_to_action",
            "certificate_definition",
            "id",
            "organizations",
            "price",
            "price_currency",
            "target_courses",
            "title",
            "type",
        ]
        read_only_fields = [
            "call_to_action",
            "certificate_definition",
            "id",
            "organizations",
            "price",
            "price_currency",
            "target_courses",
            "title",
            "type",
        ]

    def get_target_courses(self, product):
        """
        For the current product, retrieve its related courses.
        """

        context = self.context.copy()
        context["resource"] = product

        return TargetCourseSerializer(
            instance=product.target_courses.all().order_by(
                "product_target_relations__position"
            ),
            many=True,
            context=context,
        ).data

    def get_organizations(self, instance):
        """Get related organizations when in the context of a course."""
        try:
            organizations = instance.annotated_course_relations[0].organizations.all()
        except AttributeError:
            if self.context.get("course_code"):
                organizations = models.CourseProductRelation.objects.get(
                    course__code=self.context["course_code"], product=instance
                ).organizations.all()
            else:
                organizations = []

        return OrganizationSerializer(
            organizations,
            context={"request": self.context.get("request")},
            exclude_abilities=True,
            many=True,
            read_only=True,
        ).data

    def get_orders(self, instance):
        """
        If a user is authenticated, it retrieves valid or pending orders related to the
        product instance. If a course code has been provided through query
        parameters orders are also filtered by course.
        """
        request = self.context["request"]
        username = (
            request.auth["username"]
            if request.auth
            else (request.user.username if request.user.is_authenticated else None)
        )

        if username is None:
            return []

        filters = {"owner__username": username}

        if course_code := self.context.get("course_code"):
            filters["course__code"] = course_code

        return models.Order.objects.filter(
            state__in=(enums.ORDER_STATE_VALIDATED, enums.ORDER_STATE_PENDING),
            product=instance,
            **filters,
        ).values_list("pk", flat=True)

    def to_representation(self, instance):
        """
        Cache the serializer representation that does not vary from user to user
        then, if user is authenticated, add private information to the representation
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

        representation["orders"] = self.get_orders(instance)

        return representation


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
    selling_organizations = serializers.SerializerMethodField(
        "get_selling_organizations"
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
            "selling_organizations",
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
            "selling_organizations",
            "products",
            "state",
            "title",
        ]

    def get_selling_organizations(self, instance):
        """Get the course selling organizations."""
        return OrganizationSerializer(
            instance=instance.get_selling_organizations(),
            many=True,
        ).data


class CourseProductRelationSerializer(serializers.ModelSerializer):
    """
    Serialize a course product relation.
    """

    course = CourseSerializer(read_only=True)
    product = ProductSerializer(read_only=True)

    class Meta:
        model = models.CourseProductRelation
        fields = [
            "created_on",
            "course",
            "product",
        ]
        read_only_fields = [
            "created_on",
            "course",
            "product",
        ]
