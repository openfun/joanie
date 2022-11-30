"""
Helpers that can be useful throughout Joanie's core app
"""
import logging

from django.core.exceptions import ValidationError

from joanie.core import enums, models

logger = logging.getLogger(__name__)


def on_change_course_runs_to_product_target_course_relation(
    action, instance, pk_set, **kwargs
):
    """
    Signal triggered when course runs are added to a product course relation.
    Some checks are processed before course runs are linked to product course relation :
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
            models.Product.synchronize_products([instance.product])
        elif isinstance(instance, models.CourseRun):
            if action in ["post_add", "post_remove"]:
                models.Product.synchronize_products(
                    models.Product.objects.filter(course_relations__in=pk_set)
                )
            elif action == "post_clear":
                # Update all products related to this course run's course as we won't be able to
                # target only the ones that had a restriction for this course run...
                models.Product.synchronize_products(
                    models.Product.objects.filter(target_courses__course_runs=instance)
                )


def on_save_course_run(instance, **kwargs):
    """Synchronize products related to the course runs being saved."""
    instance.synchronize_with_webhooks()


def on_save_product_target_course_relation(instance, **kwargs):
    """
    Synchronize products related to the product target course relation being saved.
    """
    instance.synchronize_with_webhooks()


def on_change_course_product_relation(action, instance, pk_set, **kwargs):
    """Synchronize products related to the course/product relation being changed."""
    if action in ["post_add", "post_remove"]:
        if isinstance(instance, models.Product):
            models.Product.synchronize_products([instance])
        elif isinstance(instance, models.Course):
            models.Product.synchronize_products(
                models.Product.objects.filter(pk__in=pk_set)
            )

    elif isinstance(instance, models.Course) and action == "pre_clear":
        # When all products are cleared from a course, the only way to have access to this list
        # of products in order to re-synchronize them is to do it before the clearing
        models.Product.synchronize_products(
            instance.products.all(), visibility=enums.HIDDEN
        )

    elif isinstance(instance, models.Product) and action == "post_clear":
        models.Product.synchronize_products([instance])
