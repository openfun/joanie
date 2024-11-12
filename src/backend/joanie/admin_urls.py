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
from django.urls import include, path

from rest_framework.routers import DefaultRouter

from joanie.core.api import admin as api_admin

API_VERSION = settings.API_VERSION

# 2) Admin API
admin_router = DefaultRouter()
admin_router.register(
    "organizations", api_admin.OrganizationViewSet, basename="admin_organizations"
)
admin_router.register(
    "course-product-relations",
    api_admin.CourseProductRelationViewSet,
    basename="admin_course_product_relations",
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
admin_router.register("orders", api_admin.OrderViewSet, basename="admin_orders")
admin_router.register(
    "enrollments", api_admin.EnrollmentViewSet, basename="admin_enrollments"
)
admin_router.register("teachers", api_admin.TeacherViewSet, basename="admin_teachers")
admin_router.register("skills", api_admin.SkillViewSet, basename="admin_skills")

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
admin_organization_related_router.register(
    "addresses",
    api_admin.OrganizationAddressViewSet,
    basename="admin_organization_addresses",
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
]
