import { faker } from "@faker-js/faker";
import { TeacherFactory } from "../teacher";
import { SkillFactory } from "../skill";
import {
  BaseProduct,
  Product,
  ProductSimple,
  ProductType,
} from "@/services/api/models/Product";
import { CertificateDefinitionFactory } from "@/services/factories/certificate-definition";
import { randomNumber } from "@/utils/numbers";
import { ProductTargetCourseRelationFactory } from "@/services/api/models/ProductTargetCourseRelation";
import { OfferingFactory } from "@/services/api/models/Offerings";
import { ContractDefinitionFactory } from "@/services/factories/contract-definition";
import { QuoteDefinitionFactory } from "@/services/factories/quote-definition";

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
    offerings: OfferingFactory(2),
    contract_definition_order: ContractDefinitionFactory(),
    contract_definition_batch_order: ContractDefinitionFactory(),
    quote_definition: QuoteDefinitionFactory(),
    certification_level: faker.number.int({ min: 1, max: 8 }),
    teachers: TeacherFactory(faker.number.int({ min: 1, max: 5 })),
    skills: SkillFactory(faker.number.int({ min: 1, max: 5 })),
  };
};

export function ProductFactory(): Product;
export function ProductFactory(count: number): Product[];
export function ProductFactory(count?: number): Product | Product[] {
  if (count) return [...Array(count)].map(build);
  return build();
}

const buildLight = (): BaseProduct => {
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

export function ProductFactoryLight(): BaseProduct;
export function ProductFactoryLight(count: number): BaseProduct[];
export function ProductFactoryLight(
  count?: number,
): BaseProduct | BaseProduct[] {
  if (count) return [...Array(count)].map(buildLight);
  return buildLight();
}

const buildProductSimple = (): ProductSimple => {
  return {
    id: faker.string.uuid(),
    title: faker.company.name(),
    type: ProductType.CREDENTIAL,
    description: faker.lorem.lines(2),
    call_to_action: "Buy",
    price: faker.number.int({ min: 1000000 }),
    price_currency: "EUR",
    certificate_definition: faker.string.uuid(),
    target_courses: [faker.string.uuid()],
    offerings: [faker.string.uuid(), faker.string.uuid()],
    contract_definition_order: faker.string.uuid(),
    contract_definition_batch_order: faker.string.uuid(),
    quote_definition: faker.string.uuid(),
  };
};

export function ProductSimpleFactory(): ProductSimple;
export function ProductSimpleFactory(count: number): ProductSimple[];
export function ProductSimpleFactory(
  count?: number,
): ProductSimple | ProductSimple[] {
  if (count) return [...Array(count)].map(buildProductSimple);
  return buildProductSimple();
}
