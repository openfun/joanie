import { faker } from "@faker-js/faker";
import { Organization } from "./Organization";
import { Course } from "./Course";
import { BaseProduct, Product } from "@/services/api/models/Product";
import { CourseFactoryLight } from "@/services/factories/courses";
import { OrganizationFactory } from "@/services/factories/organizations";
import { randomNumber } from "@/utils/numbers";
import { OfferingRule } from "@/services/api/models/OfferingRule";
import { ProductFactoryLight } from "@/services/factories/product";
import { Nullable } from "@/types/utils";
import { OfferingRuleFactory } from "@/services/factories/offering-rule";

export type Offering = {
  can_edit: boolean;
  id: string;
  organizations: Organization[];
  offering_rules: OfferingRule[];
  uri?: string;
  product: BaseProduct;
  course: Course;
};

export type OfferingDummy = Omit<Offering, "id" | "product" | "course"> & {
  dummyId?: string;
  product?: Nullable<Product>;
  course?: Nullable<Course>;
};

export type DTOOffering = {
  product_id: string;
  course_id: string;
  organization_ids: string[];
};

const buildOffering = (): Offering => {
  return {
    id: faker.string.uuid(),
    can_edit: faker.datatype.boolean(),
    offering_rules: OfferingRuleFactory(2),
    course: CourseFactoryLight(),
    product: ProductFactoryLight(),
    organizations: OrganizationFactory(randomNumber(4)),
    uri: faker.internet.url(),
  };
};

export function OfferingFactory(): Offering;
export function OfferingFactory(count: number): Offering[];
export function OfferingFactory(count?: number): Offering | Offering[] {
  if (count) return [...Array(count)].map(buildOffering);
  return buildOffering();
}
