from rest_framework import serializers

from joanie.core import models


class ProductCourseRunPositionSerializer(serializers.ModelSerializer):
    """
    Represent all information about each course run inside a course product
    all course run information and course run position for the course product
    """
    resource_link = serializers.CharField(source='course_run.resource_link')
    title = serializers.CharField(source='course_run.title')
    start = serializers.CharField(source='course_run.start')
    end = serializers.CharField(source='course_run.end')
    enrollment_start = serializers.CharField(source='course_run.enrollment_start')
    enrollment_end = serializers.CharField(source='course_run.enrollment_end')

    class Meta:
        model = models.ProductCourseRunPosition
        fields = [
            'position',
            'resource_link',
            'title',
            'start',
            'end',
            'enrollment_start',
            'enrollment_end',
        ]


class CourseProductAvailableSerializer(serializers.ModelSerializer):
    """
    Represent all information about course product
    some product information and all details about course runs for the product
    """
    id = serializers.CharField(source='uid')
    title = serializers.CharField(source='product.title')
    call_to_action = serializers.CharField(source='product.call_to_action_label')
    course_runs = ProductCourseRunPositionSerializer(many=True, source='course_runs_positions')

    class Meta:
        model = models.CourseProduct
        fields = ['id', 'title', 'call_to_action', 'course_runs']


class CourseRunSerializer(serializers.ModelSerializer):
    """
    Course run model serializer
    """
    class Meta:
        model = models.CourseRun
        fields = ['resource_link', 'title', 'start', 'end', 'enrollment_start', 'enrollment_end']


class OrderSerializer(serializers.ModelSerializer):
    """
    Oder model serializer
    """
    id = serializers.CharField(source='uid')
    course_runs = CourseRunSerializer(many=True)
    owner = serializers.CharField(source='owner.username')
    product_id = serializers.CharField(source='course_product.uid')

    class Meta:
        model = models.Order
        fields = ['id', 'created_on', 'state', 'owner', 'product_id', 'course_runs']
