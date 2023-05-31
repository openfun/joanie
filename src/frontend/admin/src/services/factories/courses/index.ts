import { faker } from "@faker-js/faker";
import { Course, CourseState, Priority } from "@/services/api/models/Course";
import { OrganizationFactory } from "@/services/factories/organizations";
import { ProductFactory } from "@/services/factories/product";
import { CourseRelationToProduct } from "@/services/api/models/Relations";

const build = (): Course => {
  return {
    id: faker.datatype.uuid(),
    title: faker.company.name(),
    code: faker.company.companySuffix(),
    organizations: OrganizationFactory(2),
    product_relations: CourseRelationsToProductFactory(3),
    state: CourseStateFactory(),
  };
};

export function CourseFactory(): Course;
export function CourseFactory(count: number): Course[];
export function CourseFactory(count?: number): Course | Course[] {
  if (count) return [...Array(count)].map(build);
  return build();
}

export const CourseStateFactory = (): CourseState => {
  return {
    priority: Priority.ONGOING_CLOSED,
    datetime: new Date().toISOString(),
    call_to_action: "enroll now",
    text: "closing on",
  };
};

export const CourseRelationToProductFactory = (): CourseRelationToProduct => {
  return {
    product: ProductFactory(),
    organizations: OrganizationFactory(10),
  };
};

export const CourseRelationsToProductFactory = (
  number: number = 10
): CourseRelationToProduct[] => {
  return [...Array(number)].map(() => CourseRelationToProductFactory());
};
