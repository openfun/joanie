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
        quote_definition = factories.QuoteDefinitionFactory()
        product = factories.ProductFactory(
            quote_definition=quote_definition,
            contract_definition=contract_definition,
            skills=[skill],
            teachers=[teacher],
            certification_level=3,
        )
        offering = models.CourseProductRelation.objects.get(product=product)
        courses = factories.CourseFactory.create_batch(3)
        offerings = []
        offerings.append(
            models.ProductTargetCourseRelation(
                course=courses[0], product=product, position=2
            )
        )
        offerings[0].save()
        offerings.append(
            models.ProductTargetCourseRelation(
                course=courses[1], product=product, position=0
            )
        )
        offerings[1].save()
        offerings.append(
            models.ProductTargetCourseRelation(
                course=courses[2], product=product, position=1
            )
        )
        offerings[2].save()

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
            "quote_definition": {
                "id": str(quote_definition.id),
                "body": quote_definition.body,
                "description": quote_definition.description,
                "language": quote_definition.language,
                "name": quote_definition.name,
                "title": quote_definition.title,
            },
            "target_courses": [
                {
                    "id": str(offerings[1].id),
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
                    "is_graded": offerings[1].is_graded,
                    "position": offerings[1].position,
                },
                {
                    "id": str(offerings[2].id),
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
                    "is_graded": offerings[2].is_graded,
                    "position": offerings[2].position,
                },
                {
                    "id": str(offerings[0].id),
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
                    "is_graded": offerings[0].is_graded,
                    "position": offerings[0].position,
                },
            ],
            "instructions": "",
            "offerings": [
                {
                    "id": str(offering.id),
                    "uri": offering.uri,
                    "can_edit": offering.can_edit,
                    "course": {
                        "id": str(offering.course.id),
                        "code": offering.course.code,
                        "title": offering.course.title,
                        "state": {
                            "priority": offering.course.state["priority"],
                            "datetime": offering.course.state["datetime"],
                            "call_to_action": offering.course.state["call_to_action"],
                            "text": offering.course.state["text"],
                        },
                    },
                    "product": {
                        "price": float(offering.product.price),
                        "price_currency": settings.DEFAULT_CURRENCY,
                        "id": str(offering.product.id),
                        "title": offering.product.title,
                        "description": offering.product.description,
                        "call_to_action": offering.product.call_to_action,
                        "type": offering.product.type,
                        "certificate_definition": str(
                            offering.product.certificate_definition.id
                        ),
                        "contract_definition": str(
                            offering.product.contract_definition.id
                        ),
                        "quote_definition": str(offering.product.quote_definition.id),
                        "target_courses": [
                            str(offerings[0].course.id),
                            str(offerings[1].course.id),
                            str(offerings[2].course.id),
                        ],
                    },
                    "organizations": [
                        {
                            "code": offering.organizations.first().code,
                            "title": offering.organizations.first().title,
                            "id": str(offering.organizations.first().id),
                        }
                    ],
                    "offering_rules": [],
                }
            ],
        }
        self.assertEqual(content, expected_result)
