"""
Test suite for Product Admin API.
"""

from http import HTTPStatus

from django.conf import settings
from django.test import TestCase

from joanie.core import factories, models


class ProductAdminApiRetrieveTest(TestCase):
    """
    Test suite for the retrieve Product Admin API endpoint.
    """

    maxDiff = None

    def test_admin_api_product_get(self):
        """
        Staff user should be able to get a product through its id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        contract_definition = factories.ContractDefinitionFactory()
        skill = factories.SkillFactory(title="Python")
        teacher = factories.TeacherFactory(first_name="Joanie", last_name="Cunningham")
        product = factories.ProductFactory(
            contract_definition=contract_definition,
            skills=[skill],
            teachers=[teacher],
            certification_level=3,
        )
        offer = models.CourseProductRelation.objects.get(product=product)
        courses = factories.CourseFactory.create_batch(3)
        offers = []
        offers.append(
            models.ProductTargetCourseRelation(
                course=courses[0], product=product, position=2
            )
        )
        offers[0].save()
        offers.append(
            models.ProductTargetCourseRelation(
                course=courses[1], product=product, position=0
            )
        )
        offers[1].save()
        offers.append(
            models.ProductTargetCourseRelation(
                course=courses[2], product=product, position=1
            )
        )
        offers[2].save()

        response = self.client.get(f"/api/v1.0/admin/products/{product.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(product.id))
        expected_result = {
            "id": str(product.id),
            "title": product.title,
            "description": product.description,
            "call_to_action": product.call_to_action,
            "type": product.type,
            "price": float(product.price),
            "price_currency": "EUR",
            "certification_level": 3,
            "skills": [
                {
                    "id": str(skill.id),
                    "title": "Python",
                }
            ],
            "teachers": [
                {
                    "id": str(teacher.id),
                    "first_name": "Joanie",
                    "last_name": "Cunningham",
                }
            ],
            "certificate_definition": {
                "description": "",
                "id": str(product.certificate_definition.id),
                "name": product.certificate_definition.name,
                "template": product.certificate_definition.template,
                "title": product.certificate_definition.title,
            },
            "contract_definition": {
                "id": str(contract_definition.id),
                "title": contract_definition.title,
                "description": contract_definition.description,
                "name": contract_definition.name,
                "language": contract_definition.language,
                "body": contract_definition.body,
                "appendix": contract_definition.appendix,
            },
            "target_courses": [
                {
                    "id": str(offers[1].id),
                    "course": {
                        "id": str(courses[1].id),
                        "code": courses[1].code,
                        "title": courses[1].title,
                        "state": {
                            "priority": courses[1].state["priority"],
                            "datetime": courses[1].state["datetime"],
                            "call_to_action": courses[1].state["call_to_action"],
                            "text": courses[1].state["text"],
                        },
                    },
                    "course_runs": [],
                    "is_graded": offers[1].is_graded,
                    "position": offers[1].position,
                },
                {
                    "id": str(offers[2].id),
                    "course": {
                        "id": str(courses[2].id),
                        "code": courses[2].code,
                        "title": courses[2].title,
                        "state": {
                            "priority": courses[2].state["priority"],
                            "datetime": courses[2].state["datetime"],
                            "call_to_action": courses[2].state["call_to_action"],
                            "text": courses[2].state["text"],
                        },
                    },
                    "course_runs": [],
                    "is_graded": offers[2].is_graded,
                    "position": offers[2].position,
                },
                {
                    "id": str(offers[0].id),
                    "course": {
                        "id": str(courses[0].id),
                        "code": courses[0].code,
                        "title": courses[0].title,
                        "state": {
                            "priority": courses[0].state["priority"],
                            "datetime": courses[0].state["datetime"],
                            "call_to_action": courses[0].state["call_to_action"],
                            "text": courses[0].state["text"],
                        },
                    },
                    "course_runs": [],
                    "is_graded": offers[0].is_graded,
                    "position": offers[0].position,
                },
            ],
            "instructions": "",
            "course_relations": [
                {
                    "id": str(offer.id),
                    "uri": offer.uri,
                    "can_edit": offer.can_edit,
                    "course": {
                        "id": str(offer.course.id),
                        "code": offer.course.code,
                        "title": offer.course.title,
                        "state": {
                            "priority": offer.course.state["priority"],
                            "datetime": offer.course.state["datetime"],
                            "call_to_action": offer.course.state["call_to_action"],
                            "text": offer.course.state["text"],
                        },
                    },
                    "product": {
                        "price": float(offer.product.price),
                        "price_currency": settings.DEFAULT_CURRENCY,
                        "id": str(offer.product.id),
                        "title": offer.product.title,
                        "description": offer.product.description,
                        "call_to_action": offer.product.call_to_action,
                        "type": offer.product.type,
                        "certificate_definition": str(
                            offer.product.certificate_definition.id
                        ),
                        "contract_definition": str(
                            offer.product.contract_definition.id
                        ),
                        "target_courses": [
                            str(offers[0].course.id),
                            str(offers[1].course.id),
                            str(offers[2].course.id),
                        ],
                    },
                    "organizations": [
                        {
                            "code": offer.organizations.first().code,
                            "title": offer.organizations.first().title,
                            "id": str(offer.organizations.first().id),
                        }
                    ],
                    "offer_rules": [],
                }
            ],
        }
        self.assertEqual(content, expected_result)
