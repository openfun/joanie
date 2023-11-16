"""joanie URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path

from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from joanie.core.api import admin as api_admin
from joanie.core.api import client as api_client
from joanie.core.views import (
    BackOfficeRedirectView,
    DebugCertificateTemplateView,
    DebugDegreeTemplateView,
    DebugMailSuccessPaymentViewHtml,
    DebugMailSuccessPaymentViewTxt,
)
from joanie.lms_handler.urls import urlpatterns as lms_urlpatterns
from joanie.payment.urls import urlpatterns as payment_urlpatterns
from joanie.signature.urls import urlpatterns as signature_urlpatterns

API_VERSION = "v1.0"

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

# 2) Admin API
admin_router = DefaultRouter()
admin_router.register(
    "organizations", api_admin.OrganizationViewSet, basename="admin_organizations"
)
admin_router.register(
    "course-product-relations",
    api_admin.CourseProductRelationViewSet,
    basename="admin_products",
)
admin_router.register("products", api_admin.ProductViewSet, basename="admin_products")
admin_router.register("courses", api_admin.CourseViewSet, basename="admin_courses")
admin_router.register(
    "course-runs", api_admin.CourseRunViewSet, basename="admin_course-runs"
)
admin_router.register(
    "certificate-definitions",
    api_admin.CertificateDefinitionViewSet,
    basename="admin_certificate-definitions",
)
admin_router.register(
    "contract-definitions",
    api_admin.ContractDefinitionViewSet,
    basename="admin_contract-definitions",
)
admin_router.register("users", api_admin.UserViewSet, basename="admin_user")

# Admin API routes nested under a course
admin_course_related_router = DefaultRouter()
admin_course_related_router.register(
    "accesses", api_admin.CourseAccessViewSet, basename="admin_course_accesses"
)
admin_course_related_router.register(
    "course-runs", api_admin.CourseRunViewSet, basename="course-course-runs"
)

# Admin API routes nested under an organization
admin_organization_related_router = DefaultRouter()
admin_organization_related_router.register(
    "accesses",
    api_admin.OrganizationAccessViewSet,
    basename="admin_organization_accesses",
)

# Admin API routes nested under products
admin_product_related_router = DefaultRouter()
admin_product_related_router.register(
    "target-courses",
    api_admin.TargetCoursesViewSet,
    basename="admin_product_target_courses",
)

# Admin API routes nested under course product relations
admin_course_product_relation_related_router = DefaultRouter()
admin_course_product_relation_related_router.register(
    "order-groups",
    api_admin.NestedCourseProductRelationOrderGroupViewSet,
    basename="admin_course_product_relation_order_groups",
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        f"api/{API_VERSION}/admin/",
        include([*admin_router.urls]),
    ),
    path(
        f"api/{API_VERSION}/admin/courses/<uuid:course_id>/",
        include(admin_course_related_router.urls),
    ),
    path(
        f"api/{API_VERSION}/admin/organizations/<uuid:organization_id>/",
        include(admin_organization_related_router.urls),
    ),
    path(
        f"api/{API_VERSION}/admin/products/<uuid:product_id>/",
        include(admin_product_related_router.urls),
    ),
    path(
        f"api/{API_VERSION}/admin/course-product-relations/<uuid:course_product_relation_id>/",
        include(admin_course_product_relation_related_router.urls),
    ),
    path(
        f"api/{API_VERSION}/",
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
    ),
    re_path(
        r"^redirects/backoffice/(?P<path>.*)$",
        BackOfficeRedirectView.as_view(),
        name="redirect-to-backoffice",
    ),
]

if settings.DEBUG:
    urlpatterns = (
        urlpatterns
        + [
            path("__debug__/", include("marion.urls.debug")),
            path(
                "__debug__/mail/order_validated_html",
                DebugMailSuccessPaymentViewHtml.as_view(),
                name="debug.mail.order_validated_html",
            ),
            path(
                "__debug__/mail/order_validated_txt",
                DebugMailSuccessPaymentViewTxt.as_view(),
                name="debug.mail.order_validated_txt",
            ),
            path(
                "__debug__/pdf-templates/certificate",
                DebugCertificateTemplateView.as_view(),
                name="debug.certificate_definition.certificate",
            ),
            path(
                "__debug__/pdf-templates/degree",
                DebugDegreeTemplateView.as_view(),
                name="debug.certificate_definition.degree",
            ),
        ]
        + staticfiles_urlpatterns()
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )

    try:
        # Try to import `drf_yasg` dynamically as this dependency is installed only
        # in a development context then configure schema views and routes
        from drf_yasg import openapi, views
    except ModuleNotFoundError:
        pass
    else:
        SchemaView = views.get_schema_view(
            openapi.Info(
                title="Joanie API",
                default_version=API_VERSION,
                description="This is the Joanie API schema.",
            ),
            public=True,
            permission_classes=[permissions.AllowAny],
        )

        urlpatterns += [
            re_path(
                rf"^{API_VERSION}/swagger(?P<format>\.json|\.yaml)$",
                SchemaView.without_ui(cache_timeout=0),
                name="api-schema",
            ),
            re_path(
                rf"^{API_VERSION}/swagger/$",
                SchemaView.with_ui("swagger", cache_timeout=0),
                name="swagger-ui-schema",
            ),
            re_path(
                rf"^{API_VERSION}/redoc/$",
                SchemaView.with_ui("redoc", cache_timeout=0),
                name="redoc-schema",
            ),
        ]
