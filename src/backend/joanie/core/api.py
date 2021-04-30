"""
API endpoints
"""
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404

from rest_framework import generics, pagination, permissions, status, views
from rest_framework.response import Response

from joanie.core import exceptions, models

from . import serializers


class CourseProductsAvailableListView(views.APIView):
    """
    For a course, return all products available with its course runs
    """

    def get(self, request, code):
        """Return a list of all products available for a course"""
        course = get_object_or_404(models.Course, code=code)
        return Response(serializers.ProductSerializer(course.products, many=True).data)


class OrderPagination(pagination.PageNumberPagination):
    """Order pagination to display no more than 100 orders per page"""

    ordering = "-created_on"
    page_size = 100


class OrdersView(generics.ListAPIView):
    """
    API view allows to get all orders or create a new one with lms enrollments for a user.

    GET /api/orders/
        Return list of all orders for a user with pagination

    POST /api/orders/ with expected data:
        - id: product uid
        - resource_links: list of resource_links of all course runs selected
        Return new order just created
    """

    serializer_class = serializers.OrderSerializer
    pagination_class = OrderPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Custom queryset to get user orders"""
        user = models.User.objects.get_or_create(username=self.request.user.username)[0]
        return (
            user.orders.all()
            .select_related("owner", "product")
            .prefetch_related("enrollments__course_run")
        )

    def post(self, request):
        """
        Create an order for a selected product and enrollments for course runs selected
        then enroll user to course runs on lms
        """
        # Get the user for whom the order has to be created
        user = models.User.objects.get_or_create(username=self.request.user.username)[0]
        # Validate data given
        product_uid = request.data.get("id")
        resource_links = request.data.get("resource_links")
        if not resource_links:
            return Response({"resource_links": ["This field is required."]}, status=400)
        if not product_uid:
            return Response({"id": ["This field is required."]}, status=400)
        # Get the ordered product
        product = get_object_or_404(models.Product, uid=product_uid)
        # Now create order and enrollments
        try:
            order = product.set_order(user, resource_links)
        except exceptions.OrderAlreadyExists as err:
            return Response(status=403, data={"errors": err.args})
        except exceptions.InvalidCourseRuns as err:
            return Response(status=400, data={"errors": err.args})
        except ObjectDoesNotExist as err:
            return Response(status=404, data={"errors": err.args})
        return Response(serializers.OrderSerializer(order).data)


class AddressView(generics.ListAPIView):
    """
    API view allows to get all addresses or create or update a new one for a user.

    GET /api/addresses/
        Return list of all addresses for a user

    POST /api/addresses/ with expected data:
        - name: str, address name
        - address: str
        - postcode: str
        - city: str
        - country: str, country code
        Return new address just created

    PUT /api/addresses/<address_id>/ with expected data:
        - name: str, address name
        - address: str
        - postcode: str
        - city: str
        - country: str, country code
        Return address just updated

    DELETE /api/addresses/<address_id>/
        Delete selected address
    """

    serializer_class = serializers.AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    instance_field = "address_uid"

    def get_queryset(self):
        """Custom queryset to get user addresses"""
        user = models.User.objects.get_or_create(username=self.request.user.username)[0]
        return user.addresses.all()

    def get_instance(self, **kwargs):
        """Get address instance"""
        return get_object_or_404(models.Address, uid=kwargs[self.instance_field])

    def put(self, request, **kwargs):
        """Update address selected with new data"""
        if self.instance_field and self.instance_field in kwargs:
            obj = self.get_instance(**kwargs)
            # User authenticated has to be the address owner
            if obj.owner.username == self.request.user.username:
                serializer = self.serializer_class(instance=obj, data=request.data)
                if not serializer.is_valid():
                    return Response(
                        {"errors": serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                serializer.save()
                return Response({"data": serializer.data})
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """Create a new address for user authenticated"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = models.User.objects.get_or_create(username=self.request.user.username)[0]
        serializer.save(owner=user)
        return Response(status=status.HTTP_201_CREATED, data={"data": serializer.data})

    def delete(self, request, **kwargs):
        """Delete address selected"""
        obj = self.get_instance(**kwargs)
        # User authenticated has to be the address owner
        if obj.owner.username == self.request.user.username:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)
