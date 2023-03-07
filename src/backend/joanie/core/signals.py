"""
Helpers that can be useful throughout Joanie's core app
"""
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from joanie.core import enums, models
from joanie.core.utils import webhooks

logger = logging.getLogger(__name__)


def on_change_course_runs_to_product_target_course_relation(
    action, instance, pk_set, **kwargs
):
    """
    Signal triggered when course runs are added to a product / target course relation.
    Some checks are processed before course runs are linked to product / target course relation :
        1. Check that course runs linked are related to the relation course
    """
    if action == "pre_add":
        # Instance can be a `ProductTargetCourseRelation` or a `CourseRun`. In the case instance
        # is a CourseRun, we have to retrieve manually product course relations instances.
        if isinstance(instance, models.ProductTargetCourseRelation):
            relations = [instance]
            course_runs_set = pk_set
        else:
            relations = models.ProductTargetCourseRelation.objects.filter(
                pk__in=pk_set
            ).select_related("course")
            course_runs_set = {instance.pk}

        for relation in relations:
            # Check that all involved course runs rely on the relation course
            if relation.course.course_runs.filter(
                pk__in=course_runs_set
            ).count() != len(course_runs_set):
                raise ValidationError(
                    {
                        "course_runs": [
                            (
                                "Limiting a course to targeted course runs can only be done"
                                " for course runs already belonging to this course."
                            )
                        ]
                    }
                )

    # Webhooks synchronization
    elif action in ["post_add", "post_remove", "post_clear"]:
        if isinstance(instance, models.ProductTargetCourseRelation):
            serialized_course_runs = (
                models.Product.get_equivalent_serialized_course_runs_for_products(
                    [instance.product]
                )
            )
        elif isinstance(instance, models.CourseRun):
            if action in ["post_add", "post_remove"]:
                serialized_course_runs = (
                    models.Product.get_equivalent_serialized_course_runs_for_products(
                        models.Product.objects.filter(
                            target_course_relations__in=pk_set
                        )
                    )
                )
            elif action == "post_clear":
                # Update all products related to this course run's course as we won't be able to
                # target only the ones that had a restriction for this course run...
                serialized_course_runs = (
                    models.Product.get_equivalent_serialized_course_runs_for_products(
                        models.Product.objects.filter(
                            target_courses__course_runs=instance
                        )
                    )
                )

        webhooks.synchronize_course_runs(serialized_course_runs)


def on_save_course_run(instance, **kwargs):
    """Synchronize the course run and products related to the course run being saved."""
    # Synchronize the course run itself
    serialized_course_runs = [instance.get_serialized()]

    # Synchronize the related products by recomputing their equivalent serialized course run
    serialized_course_runs.extend(
        instance.get_equivalent_serialized_course_runs_for_related_products()
    )
    webhooks.synchronize_course_runs(serialized_course_runs)


def on_save_product_target_course_relation(instance, **kwargs):
    """
    Synchronize products related to the product target course relation being saved.
    """
    serialized_course_runs = (
        models.Product.get_equivalent_serialized_course_runs_for_products(
            [instance.product]
        )
    )
    webhooks.synchronize_course_runs(serialized_course_runs)


def on_change_course_product_relation(action, instance, pk_set, **kwargs):
    """Synchronize products related to the course/product relation being changed."""
    if isinstance(instance, models.Course):
        if action == "post_add":
            serialized_course_runs = (
                models.Product.get_equivalent_serialized_course_runs_for_products(
                    models.Product.objects.filter(pk__in=pk_set), courses=[instance]
                )
            )
        elif action == "pre_remove":
            serialized_course_runs = (
                models.Product.get_equivalent_serialized_course_runs_for_products(
                    models.Product.objects.filter(pk__in=pk_set),
                    courses=[instance],
                    visibility=enums.HIDDEN,
                )
            )
        elif action in ["pre_clear"]:
            # When all products are cleared from a course, the only way to have access to this list
            # of products in order to re-synchronize them is to do it before the clearing
            serialized_course_runs = (
                models.Product.get_equivalent_serialized_course_runs_for_products(
                    instance.products.all(), courses=[instance], visibility=enums.HIDDEN
                )
            )
        else:
            return

    elif isinstance(instance, models.Product):
        if action == "post_add":
            serialized_course_runs = (
                models.Product.get_equivalent_serialized_course_runs_for_products(
                    [instance]
                )
            )
        elif action == "pre_clear":
            serialized_course_runs = (
                models.Product.get_equivalent_serialized_course_runs_for_products(
                    [instance], visibility=enums.HIDDEN
                )
            )
        elif action == "pre_remove":
            serialized_course_runs = (
                models.Product.get_equivalent_serialized_course_runs_for_products(
                    [instance],
                    models.Course.objects.filter(pk__in=pk_set),
                    visibility=enums.HIDDEN,
                )
            )
        else:
            return
    else:
        return

    webhooks.synchronize_course_runs(serialized_course_runs)


def base_create_notification(instance, course_wishes, action=None):
    """
    Create a notification instance to each user who has a course_wish to participate to
    the course related to the saved instance
    """
    for course_wish in course_wishes:
        course_wish_ctype = ContentType.objects.get_for_model(course_wish._meta.model)
        instance_ctype = ContentType.objects.get_for_model(instance._meta.model)

        notif_data = {
            "owner": course_wish.owner,
            "notif_subject_ctype": course_wish_ctype,
            "notif_subject_id": course_wish.id,
            "notif_object_ctype": instance_ctype,
            "notif_object_id": instance.id,
        }
        if action:
            notif_data["action"] = action

        models.Notification.objects.get_or_create(
            **notif_data
        )


def post_save_course_run_notification(instance, created, **kwargs):
    """
    Create a notification instance to each user who has a course_wish to participate to
    the course of the saved course run.
    """
    if created:
        course_wishes = instance.course.wished_in_wishlists.all()
        base_create_notification(instance, course_wishes, models.Notification.NOTIF_ACTION_CREATE)


def post_save_product_target_course_relation_notification(instance, created, **kwargs):
    """
    Create a notification instance to each user who has a course_wish to participate to
    the course of the saved course run.
    """
    if created:
        course_wishes = instance.course.wished_in_wishlists.all()
        base_create_notification(instance.product, course_wishes, models.Notification.NOTIF_ACTION_CREATE)


def post_add_m2m_product_target_course_notification(action, instance, pk_set, **kwargs):
    """
    Create a notification instance to each user who has a course_wish to participate to
    a target_course of the saved product.
    """
    if action == "post_add":
        course_wishes = models.CourseWish.objects.filter(course__id__in=pk_set)
        base_create_notification(instance, course_wishes, models.Notification.NOTIF_ACTION_ADD)
