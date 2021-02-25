import jwt

from rest_framework import generics
from rest_framework import pagination
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import views

from django.conf import settings
from django.shortcuts import get_object_or_404

from joanie.core import models
from joanie.core import errors

from . import serializers


class OrdersAccessPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        # TODO: check token is valid
        return True


class CourseProductsAvailableListView(views.APIView):  # FIXME: APIView ?
    """
    For a course, return all products available and its course runs
    """
    def get(self, request, code):
        course = models.Course.objects.get(code=code)
        serializer = serializers.CourseProductAvailableSerializer(
            many=True,
            instance=course.course_products,
            # TODO: add a sort!
        )
        return Response(serializer.data)


class OrderPagination(pagination.PageNumberPagination):
    ordering = "-created_on"
    page_size = 100


# TODO: protect view with permission -> check token is valid!
class OrdersView(generics.ListAPIView):
    """
    GET /api/orders/ return list of all orders for a user with pagination
    POST /api/orders/ with data: course product uid, resource_links of all course runs selected
                    -> return new order just created
    """
    serializer_class = serializers.OrderSerializer
    pagination_class = OrderPagination
    permissions = [OrdersAccessPermission]

    def get_user(self):
        # TODO: try except failure decode
        authorization_header = self.request.headers.get("Authorization")
        # FIXME return failure
        if not authorization_header:
            return Response("Missing authentication.", status=401)
        access_token = authorization_header.split(' ')[1]  # Bearer XXXXX

        # TODO: return failure if token pourri (decoding failure)
        # TODO: is_valid mettre dans une permission custom le check token valid
        # (exp((session de l'utilisateur va périmer)), iat)
        claim = jwt.decode(
            access_token,
            getattr(settings, 'JWT_PRIVATE_SIGNING_KEY'),
            algorithms=getattr(settings, 'JWT_ALGORITHM'),
        )
        username = claim['username']
        return models.User.objects.get_or_create(username=username)[0]

    def get_queryset(self):
        user = self.get_user()
        return user.orders.all()

    def post(self, request):
        user = self.get_user()
        course_product_uid = request.data.get('id')
        resource_links = request.data.get('resource_links')
        if not resource_links:
            return Response({"resource_links": ["This field is required."]}, status=400)
        if not course_product_uid:
            return Response({"id": ["This field is required."]}, status=400)
        course_product = get_object_or_404(models.CourseProduct, uid=course_product_uid)

        # Now create order and enrollments
        try:
            order = course_product.set_order(user, resource_links)
        except errors.OrderAlreadyExists as e:
            return Response(status=403, data={"errors": e.args})
        except Exception as e:
            return Response(status=500, data={"errors": e.args})
        return Response(serializers.OrderSerializer(order).data)
