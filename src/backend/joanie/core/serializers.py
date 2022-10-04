"""Serializers for api."""

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from dynamic_rest.serializers import DynamicModelSerializer,DynamicRelationField
from dynamic_rest.fields import DynamicMethodField

from djmoney.contrib.django_rest_framework import MoneyField
from rest_framework import serializers

from joanie.core import models

#class DynamicMethodFieldModelSerializer(DynamicModelSerializer):
    


class CertificationDefinitionSerializer(DynamicModelSerializer):
    """
    Serialize information about a certificate definition
    """

    description = serializers.CharField(read_only=True)

    class Meta:
        model = models.CertificateDefinition
        fields = ["description", "name", "title"]
        read_only_fields = ["description", "name", "title"]


class OrganizationSerializer(DynamicModelSerializer):
    """
    Serialize all non-sensitive information about an organization
    """

    class Meta:
        model = models.Organization
        fields = ["code", "title", "logo"]
        read_only_fields = ["code", "title", "logo"]


class TargetCourseSerializer(DynamicModelSerializer):
    """
    Serialize all information about a target course.
    """

    #course_runs = DynamicMethodField(read_only=True, requires=['target_course_runs'])# """deferred=True,""" si true n'arrive pas à afficher
    course_runs = DynamicMethodField(read_only=True, )# """deferred=True,""" si true n'arrive pas à afficher par url
    organization = OrganizationSerializer(read_only=True)
    position = DynamicMethodField(read_only=True)
    is_graded = DynamicMethodField(read_only=True)

    class Meta:
        model = models.Course
        fields = [
            "code",
            "course_runs",
            "is_graded",
            "organization",
            "position",
            "title",
        ]
        read_only_fields = [
            "code",
            "course_runs",
            "is_graded",
            "organization",
            "position",
            "title",
        ]
        #deferred_fields = ['course_runs']

    @property
    def context_product(self):
        """
        Retrieve the product provided in context. If no product is provided, it raises
        a ValidationError.
        """
        try:
            return self.context["product"]
        except KeyError as exception:
            raise serializers.ValidationError(
                'TargetCourseSerializer context must contain a "product" property.'
            ) from exception

    def get_position(self, target_course):
        """
        Retrieve the position of the course related to its product_relation
        """
        return target_course.product_relations.get(
            product=self.context_product
        ).position

    def get_is_graded(self, target_course):
        """
        Retrieve the `is_graded` state of the course related to its product_relation
        """
        return target_course.product_relations.get(
            product=self.context_product
        ).is_graded

    def get_course_runs(self, target_course):
        """
        Return related course runs ordered by start date asc
        """
        course_runs = self.context_product.target_course_runs.filter(
            course=target_course
        ).order_by("start")

        return CourseRunSerializer(course_runs, many=True).data


class ProductSerializer(DynamicModelSerializer):
    """
    Product serializer including
        - certificate information if there is
        - targeted courses with its course runs
            - If user is authenticated, we try to retrieve enrollment related
              to each course run.
        - order if user is authenticated
    """

    id = serializers.CharField(read_only=True, source="uid")
    certificate = CertificationDefinitionSerializer(
        read_only=True, source="certificate_definition",
    )
    price = MoneyField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=0,
        read_only=True,
    )
    target_courses = DynamicMethodField(read_only=True, deferred=True)#,#,requires=['location.cat_set.*'],
       #deferred=False)

    class Meta:
        model = models.Product
        fields = [
            "call_to_action",
            "certificate",
            "id",
            "price",
            "price_currency",
            "target_courses",
            "title",
            "type",
        ]
        read_only_fields = [
            "call_to_action",
            "certificate",
            "id",
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
        context.update({"product": product})

        target_course =  TargetCourseSerializer(
            instance=models.Course.objects.filter(
                product_relations__product=product
            ).order_by("product_relations__position"),
            many=True,
            context=context,
           # deferred=False unexpected
        )
        return target_course.data


class CourseSerializer(DynamicModelSerializer):
    """
    Serialize all information about a course.
    """

    #organization = DynamicRelationField('OrganizationSerializer', deferred=False, read_only=True)
    #products = DynamicRelationField('ProductSerializer',deferred=False, many=True,read_only=True,  embed=False )#, embed=True
    organization = DynamicRelationField('OrganizationSerializer', deferred=False,many=False, embed=True,read_only=True)
    products = DynamicRelationField('ProductSerializer', deferred=True, many=True,read_only=True)#embed=True
    #orders = DynamicRelationField('OrderSerializer', deferred=True, many=True, read_only=True)
    
    class Meta:
        model = models.Course
        name="Course"
        fields = [
            "code",
            "organization",
        #   "orders",
            "products",
            "title",
        ]
        read_only_fields = [
            "code",
            "organization",
         #   "orders",
            "products",
            "title",
            
        ]

    def to_representation(self, instance):
        """
        Cache the serializer representation that does not vary from user to user
        then, if user is authenticated, add private information to the representation
        """
        cache_key = instance.get_cache_key()
        representation = cache.get(cache_key)

        if representation is None:
            representation = super().to_representation(instance)
            cache.set(
                cache_key,
                representation,
                settings.JOANIE_ANONYMOUS_COURSE_SERIALIZER_CACHE_TTL,
            )

        return representation


class CourseRunSerializer(DynamicModelSerializer):
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


class EnrollmentSerializer(DynamicModelSerializer):
    """
    Enrollment model serializer
    """

    id = serializers.CharField(source="uid", read_only=True, required=False)
    course_run = CourseRunSerializer(read_only=True)

    class Meta:
        model = models.Enrollment
        fields = ["id", "course_run", "is_active", "state"]
        read_only_fields = ["id", "state"]

    def create(self, validated_data):
        """
        Retrieve the course run ressource through the provided resource_link
        then try to create the enrollment ressource.
        """
        resource_link = self.initial_data["course_run"]
        try:
            course_run = models.CourseRun.objects.get(resource_link=resource_link)
        except models.CourseRun.DoesNotExist as exception:
            message = (
                f'A course run with resource link "{resource_link}" does not exist.'
            )
            raise serializers.ValidationError({"__all__": [message]}) from exception

        validated_data["course_run"] = course_run

        return super().create(validated_data=validated_data)

    def update(self, instance, validated_data):
        """
        Restrict the values that can be set from the API for the state field to "set".
        The "failed" state can only be set by the LMSHandler.
        """
        validated_data.pop("course_run", None)
        return super().update(instance, validated_data)


class OrderSerializer(serializers.ModelSerializer):
    """
    Order model serializer
    """

    id = serializers.CharField(source="uid", read_only=True, required=False)
    owner = serializers.CharField(
        source="owner.username", read_only=True, required=False
    )
    course = serializers.SlugRelatedField(
        queryset=models.Course.objects.all(), slug_field="code"
    )
    total = MoneyField(
        coerce_to_string=False,
        decimal_places=2,
        max_digits=9,
        min_value=0,
        read_only=True,
        required=False,
    )
    product = serializers.SlugRelatedField(
        queryset=models.Product.objects.all(), slug_field="uid"
    )
    enrollments = DynamicMethodField(read_only=True) 
    """ requires=[
            'profile.preferred_first_name',
            'profile.preferred_last_name'
        ]) """
        

    target_courses = DynamicMethodField(read_only=True)
    """, requires=[
            'profile.preferred_first_name',
            'profile.preferred_last_name'
        ]"""
    main_proforma_invoice = serializers.SlugRelatedField(
        read_only=True, slug_field="reference"
    )
    certificate = serializers.SlugRelatedField(read_only=True, slug_field="uid")

    class Meta:
        model = models.Order
        fields = [
            "course",
            "created_on",
            "certificate",
            "enrollments",
            "id",
            "main_proforma_invoice",
            "owner",
            "total",
            "total_currency",
            "product",
            "state",
            "target_courses",
        ]
        read_only_fields = [
            "certificate",
            "created_on",
            "enrollments",
            "id",
            "main_proforma_invoice",
            "owner",
            "total",
            "total_currency",
            "state",
            "target_courses",
        ]

    @staticmethod
    def get_target_courses(obj):
        """Compute the serialized value for the "target_courses" field."""
        return (
            models.Course.objects.filter(order_relations__order=obj)
            .order_by("order_relations__position")
            .values_list("code", flat=True)
        )

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
        """Make the "course" and "product" fields read_only only on update."""
        validated_data.pop("course", None)
        validated_data.pop("product", None)
        return super().update(instance, validated_data)


class AddressSerializer(serializers.ModelSerializer):
    """
    Address model serializer
    """

    id = serializers.CharField(source="uid", read_only=True, required=False)

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


class CertificateSerializer(DynamicModelSerializer):
    """
    Certificate model serializer
    """

    id = serializers.CharField(source="uid", read_only=True, required=False)

    class Meta:
        model = models.Certificate
        fields = ["id"]
        read_only_fields = ["id"]
