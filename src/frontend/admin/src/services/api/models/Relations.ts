import { faker } from "@faker-js/faker";
import { Organization } from "./Organization";
import { Course } from "./Course";
import { Product } from "@/services/api/models/Product";
import { CourseFactoryLight } from "@/services/factories/courses";
import { OrganizationFactory } from "@/services/factories/organizations";
import { randomNumber } from "@/utils/numbers";
import { OrderGroup } from "@/services/api/models/OrderGroup";
import { ProductFactoryLight } from "@/services/factories/product";
import { Nullable } from "@/types/utils";
import { OrderGroupFactory } from "@/services/factories/order-group";

export type CourseProductRelation = {
  can_edit: boolean;
  id: string;
  organizations: Organization[];
  order_groups: OrderGroup[];
  uri?: string;
  product: Product;
  course: Course;
};

export type CourseProductRelationDummy = Omit<
  CourseProductRelation,
  "id" | "product" | "course"
> & {
  dummyId?: string;
  product?: Nullable<Product>;
  course?: Nullable<Course>;
};

export type DTOCourseProductRelation = {
  product_id: string;
  course_id: string;
  organization_ids: string[];
};

const buildCourseProductRelation = (): CourseProductRelation => {
  return {
    id: faker.string.uuid(),
    can_edit: faker.datatype.boolean(),
    order_groups: OrderGroupFactory(2),
    course: CourseFactoryLight(),
    product: ProductFactoryLight(),
    organizations: OrganizationFactory(randomNumber(4)),
    uri: faker.internet.url(),
  };
};

export function CourseProductRelationFactory(): CourseProductRelation;
export function CourseProductRelationFactory(
  count: number,
): CourseProductRelation[];
export function CourseProductRelationFactory(
  count?: number,
): CourseProductRelation | CourseProductRelation[] {
  if (count) return [...Array(count)].map(buildCourseProductRelation);
  return buildCourseProductRelation();
}
