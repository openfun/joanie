import { faker } from "@faker-js/faker";
import { Product, ProductType } from "@/services/api/models/Product";
import { CertificateDefinitionFactory } from "@/services/factories/certificate-definition";
import { randomNumber } from "@/utils/numbers";
import { ProductTargetCourseRelationFactory } from "@/services/api/models/ProductTargetCourseRelation";
import { ProductRelationToCourseFactory } from "@/services/api/models/Relations";
import { ContractDefinitionFactory } from "@/services/factories/contract-definition";

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
    target_courses: ProductTargetCourseRelationFactory(randomNumber(2)),
    course_relations: ProductRelationToCourseFactory(2),
    contract_definition: ContractDefinitionFactory(),
  };
};

export function ProductFactory(): Product;
export function ProductFactory(count: number): Product[];
export function ProductFactory(count?: number): Product | Product[] {
  if (count) return [...Array(count)].map(build);
  return build();
}

const buildLight = (): Product => {
  return {
    id: faker.string.uuid(),
    title: faker.company.name(),
    type: ProductType.CREDENTIAL,
    description: faker.lorem.lines(2),
    call_to_action: "Buy",
    price: faker.number.int({ min: 1000000 }),
    price_currency: "EUR",
  };
};

export function ProductFactoryLight(): Product;
export function ProductFactoryLight(count: number): Product[];
export function ProductFactoryLight(count?: number): Product | Product[] {
  if (count) return [...Array(count)].map(buildLight);
  return buildLight();
}
