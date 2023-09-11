import { faker } from "@faker-js/faker";
import { Product, ProductType } from "@/services/api/models/Product";
import { CertificateDefinitionFactory } from "@/services/factories/certificate-definition";
import { ProductRelationToCourseFactory } from "@/services/api/models/Relations";
import { randomNumber } from "@/utils/numbers";
import { ProductTargetCourseRelationFactory } from "@/services/api/models/ProductTargetCourseRelation";

const build = (): Product => {
  return {
    id: faker.string.uuid(),
    title: faker.company.name(),
    type: ProductType.CREDENTIAL,
    description: faker.lorem.lines(2),
    call_to_action: "Buy",
    price: faker.number.int({ min: 1000000 }),
    price_currency: "EUR",
    certificate_definition: CertificateDefinitionFactory(),
    courses: ProductRelationToCourseFactory(randomNumber(5)),
    target_courses: ProductTargetCourseRelationFactory(randomNumber(2)),
  };
};

export function ProductFactory(): Product;
export function ProductFactory(count: number): Product[];
export function ProductFactory(count?: number): Product | Product[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
