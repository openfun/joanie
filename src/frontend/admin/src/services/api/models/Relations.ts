import { faker } from "@faker-js/faker";
import { Organization } from "./Organization";
import { Course } from "./Course";
import { Product } from "@/services/api/models/Product";
import { CourseFactory } from "@/services/factories/courses";
import { OrganizationFactory } from "@/services/factories/organizations";
import { randomNumber } from "@/utils/numbers";

export type CourseRelationToProduct = {
  product: Product;
  organizations: Organization[];
};

export type DTOCourseRelationToProduct = {
  product: string;
  organizations: string[];
};

export type ProductRelationToCourse = {
  id?: string;
  course: Course;
  graded?: boolean;
  organizations: Organization[];
};

const buildProductRelationToCourse = (): ProductRelationToCourse => {
  return {
    id: faker.string.uuid(),
    course: CourseFactory(),
    organizations: OrganizationFactory(randomNumber(4)),
  };
};

export function ProductRelationToCourseFactory(): ProductRelationToCourse;
export function ProductRelationToCourseFactory(
  count: number,
): ProductRelationToCourse[];
export function ProductRelationToCourseFactory(
  count?: number,
): ProductRelationToCourse | ProductRelationToCourse[] {
  if (count) return [...Array(count)].map(buildProductRelationToCourse);
  return buildProductRelationToCourse();
}
