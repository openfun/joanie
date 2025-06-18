import { faker } from "@faker-js/faker";
import { Organization } from "./Organization";
import { Course } from "./Course";
import { BaseProduct, Product } from "@/services/api/models/Product";
import { CourseFactoryLight } from "@/services/factories/courses";
import { OrganizationFactory } from "@/services/factories/organizations";
import { randomNumber } from "@/utils/numbers";
import { OfferRule } from "@/services/api/models/OfferRule";
import { ProductFactoryLight } from "@/services/factories/product";
import { Nullable } from "@/types/utils";
import { OfferRuleFactory } from "@/services/factories/offer-rule";

export type Offer = {
  can_edit: boolean;
  id: string;
  organizations: Organization[];
  offer_rules: OfferRule[];
  uri?: string;
  product: BaseProduct;
  course: Course;
};

export type OfferDummy = Omit<Offer, "id" | "product" | "course"> & {
  dummyId?: string;
  product?: Nullable<Product>;
  course?: Nullable<Course>;
};

export type DTOOffer = {
  product_id: string;
  course_id: string;
  organization_ids: string[];
};

const buildOffer = (): Offer => {
  return {
    id: faker.string.uuid(),
    can_edit: faker.datatype.boolean(),
    offer_rules: OfferRuleFactory(2),
    course: CourseFactoryLight(),
    product: ProductFactoryLight(),
    organizations: OrganizationFactory(randomNumber(4)),
    uri: faker.internet.url(),
  };
};

export function OfferFactory(): Offer;
export function OfferFactory(count: number): Offer[];
export function OfferFactory(count?: number): Offer | Offer[] {
  if (count) return [...Array(count)].map(buildOffer);
  return buildOffer();
}
