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
        relation = models.CourseProductRelation.objects.get(product=product)
        courses = factories.CourseFactory.create_batch(3)
        relations = []
        relations.append(
            models.ProductTargetCourseRelation(
                course=courses[0], product=product, position=2
            )
        )
        relations[0].save()
        relations.append(
            models.ProductTargetCourseRelation(
                course=courses[1], product=product, position=0
            )
        )
        relations[1].save()
        relations.append(
            models.ProductTargetCourseRelation(
                course=courses[2], product=product, position=1
            )
        )
        relations[2].save()

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
                    "id": str(relations[1].id),
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
                    "is_graded": relations[1].is_graded,
                    "position": relations[1].position,
                },
                {
                    "id": str(relations[2].id),
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
                    "is_graded": relations[2].is_graded,
                    "position": relations[2].position,
                },
                {
                    "id": str(relations[0].id),
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
                    "is_graded": relations[0].is_graded,
                    "position": relations[0].position,
                },
            ],
            "instructions": "",
            "course_relations": [
                {
                    "id": str(relation.id),
                    "uri": relation.uri,
                    "can_edit": relation.can_edit,
                    "course": {
                        "id": str(relation.course.id),
                        "code": relation.course.code,
                        "title": relation.course.title,
                        "state": {
                            "priority": relation.course.state["priority"],
                            "datetime": relation.course.state["datetime"],
                            "call_to_action": relation.course.state["call_to_action"],
                            "text": relation.course.state["text"],
                        },
                    },
                    "product": {
                        "price": float(relation.product.price),
                        "price_currency": settings.DEFAULT_CURRENCY,
                        "id": str(relation.product.id),
                        "title": relation.product.title,
                        "description": relation.product.description,
                        "call_to_action": relation.product.call_to_action,
                        "type": relation.product.type,
                        "certificate_definition": str(
                            relation.product.certificate_definition.id
                        ),
                        "contract_definition": str(
                            relation.product.contract_definition.id
                        ),
                        "target_courses": [
                            str(relations[0].course.id),
                            str(relations[1].course.id),
                            str(relations[2].course.id),
                        ],
                    },
                    "organizations": [
                        {
                            "code": relation.organizations.first().code,
                            "title": relation.organizations.first().title,
                            "id": str(relation.organizations.first().id),
                        }
                    ],
                    "offer_rules": [],
                }
            ],
        }
        self.assertEqual(content, expected_result)
