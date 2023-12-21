import { faker } from "@faker-js/faker";
import {
  Course,
  CourseRoles,
  CourseState,
  Priority,
} from "@/services/api/models/Course";
import { OrganizationFactory } from "@/services/factories/organizations";
import { CourseRelationToProduct } from "@/services/api/models/Relations";
import { AccessesFactory } from "@/services/factories/accesses";
import { OrderGroupFactory } from "@/services/factories/order-group";
import { ProductFactoryLight } from "@/services/factories/product";
import { CourseRunFactory } from "@/services/factories/courses-runs";

const build = (): Course => {
  const result: Course = {
    id: faker.string.uuid(),
    title: faker.company.name(),
    code: faker.number.hex({ min: 0, max: 65535 }), // 'af17'
    is_graded: true,
    organizations: OrganizationFactory(2),
    product_relations: CourseRelationsToProductFactory(1),
    state: CourseStateFactory(),
    accesses: AccessesFactory(Object.values(CourseRoles), 3),
  };

  return {
    ...result,
    courses_runs: CourseRunFactory(2, result),
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
    product: ProductFactoryLight(),
    organizations: OrganizationFactory(2),
    id: faker.string.uuid(),
    can_edit: faker.datatype.boolean(),
    order_groups: OrderGroupFactory(2),
    uri: faker.internet.url(),
  };
};

export const CourseRelationsToProductFactory = (
  number: number = 10,
): CourseRelationToProduct[] => {
  return [...Array(number)].map(() => CourseRelationToProductFactory());
};
