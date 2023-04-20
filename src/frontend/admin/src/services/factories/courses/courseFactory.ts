import { faker } from "@faker-js/faker";
import { Course, CourseState, Priority } from "@/services/api/models/Course";
import { createDummyOrganizations } from "@/services/factories/organizations/organizationFactory";
import { createDummyProduct } from "@/services/factories/product/productFactory";
import { CourseRelationToProduct } from "@/services/api/models/Relations";

export const createDummyCourse = (): Course => {
  return {
    id: faker.datatype.uuid(),
    title: faker.company.name(),
    code: faker.company.companySuffix(),
    organizations: createDummyOrganizations(2),
    product_relations: createDummyCourseRelationsToProduct(3),
    state: createDummyCourseState(),
  };
};

export const createDummyCourses = (number: number = 10): Course[] => {
  return [...Array(number)].map(() => createDummyCourse());
};

export const createDummyCourseState = (): CourseState => {
  return {
    priority: Priority.ONGOING_CLOSED,
    datetime: new Date().toISOString(),
    call_to_action: "enroll now",
    text: "closing on",
  };
};

export const createDummyCourseRelationToProduct =
  (): CourseRelationToProduct => {
    return {
      product: createDummyProduct(),
      organizations: createDummyOrganizations(),
    };
  };

export const createDummyCourseRelationsToProduct = (
  number: number = 10
): CourseRelationToProduct[] => {
  return [...Array(number)].map(() => createDummyCourseRelationToProduct());
};
