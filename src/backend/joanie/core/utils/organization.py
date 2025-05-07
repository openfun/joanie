"""Util to get the organization with the least binding orders count"""

from django.db.models import Count, Exists, OuterRef, Q

from joanie.core import enums, models


def get_least_active_organization(product, course, enrollment=None):
    """
    Return the organization with the least binding orders count
    for a given product and course.
    """
    course_id = course.id if course else enrollment.course_run.course_id

    try:
        course_relation = product.course_relations.get(course_id=course_id)
    except models.CourseProductRelation.DoesNotExist:
        return None

    order_count_filter = Q(order__product=product) & Q(
        order__state__in=(*enums.ORDER_STATES_BINDING, enums.ORDER_STATE_TO_OWN)
    )

    if enrollment:
        order_count_filter &= Q(order__enrollment=enrollment)
    else:
        order_count_filter &= Q(order__course=course)

    try:
        organizations = course_relation.organizations.annotate(
            order_count=Count("order", filter=order_count_filter, distinct=True),
            is_author=Exists(
                models.Organization.objects.filter(
                    pk=OuterRef("pk"), courses__id=course_id
                )
            ),
        )

        return organizations.order_by("order_count", "-is_author", "?").first()
    except models.Organization.DoesNotExist:
        return None
