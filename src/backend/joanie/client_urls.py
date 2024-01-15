"""joanie URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.urls import include, path, re_path

from rest_framework.routers import DefaultRouter

from joanie.core.api import client as api_client
from joanie.lms_handler.urls import urlpatterns as lms_urlpatterns
from joanie.payment.urls import urlpatterns as payment_urlpatterns
from joanie.signature.urls import urlpatterns as signature_urlpatterns

# 1) Client API

# - Main endpoints
router = DefaultRouter()
router.register("addresses", api_client.AddressViewSet, basename="addresses")
router.register("certificates", api_client.CertificateViewSet, basename="certificates")
router.register(
    "contracts",
    api_client.ContractViewSet,
    basename="contracts",
)
router.register(
    "contract_definitions",
    api_client.ContractDefinitionViewset,
    basename="contract_definitions",
)
router.register("courses", api_client.CourseViewSet, basename="courses")
router.register("course-runs", api_client.CourseRunViewSet, basename="course-runs")
router.register("enrollments", api_client.EnrollmentViewSet, basename="enrollments")
router.register("orders", api_client.OrderViewSet, basename="orders")
router.register(
    "organizations", api_client.OrganizationViewSet, basename="organizations"
)
router.register(
    "course-product-relations",
    api_client.CourseProductRelationViewSet,
    basename="course-product-relations",
)
router.register("users", api_client.UserViewSet, basename="users")

# - Routes nested under a course
course_related_router = DefaultRouter()
course_related_router.register(
    "accesses",
    api_client.CourseAccessViewSet,
    basename="course_accesses",
)
course_related_router.register(
    "contracts",
    api_client.NestedCourseContractViewSet,
    basename="course_contracts",
)
course_related_router.register(
    "course-runs",
    api_client.CourseRunViewSet,
    basename="course_course_runs",
)
course_related_router.register(
    "products",
    api_client.CourseProductRelationViewSet,
    basename="course_product_relations",
)
course_related_router.register(
    "orders",
    api_client.NestedOrderCourseViewSet,
    basename="orders_course",
)

# - Routes nested under an organization
organization_related_router = DefaultRouter()
organization_related_router.register(
    "accesses",
    api_client.OrganizationAccessViewSet,
    basename="organization_accesses",
)
organization_related_router.register(
    "contracts",
    api_client.NestedOrganizationContractViewSet,
    basename="organization_contracts",
)
organization_related_router.register(
    "course-product-relations",
    api_client.CourseProductRelationViewSet,
    basename="course_product_relations_per_organization",
)
organization_related_router.register(
    "courses",
    api_client.CourseViewSet,
    basename="course_per_organization",
)

urlpatterns = [
    path(
        f"api/{settings.API_VERSION}/",
        include(
            [
                *router.urls,
                *lms_urlpatterns,
                *payment_urlpatterns,
                *signature_urlpatterns,
                re_path(
                    r"^courses/(?P<course_id>[0-9a-z-]*)/",
                    include(course_related_router.urls),
                ),
                re_path(
                    r"^organizations/(?P<organization_id>[0-9a-z-]*)/",
                    include(organization_related_router.urls),
                ),
            ]
        ),
    )
]
