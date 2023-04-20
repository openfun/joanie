import { faker } from "@faker-js/faker";
import { Product } from "@/services/api/models/Product";
import { createDummyCertificateDefinition } from "@/services/factories/certificate-definition/certificationDefinitionFactory";

export const createDummyProduct = (): Product => {
  return {
    id: faker.datatype.uuid(),
    title: faker.company.name(),
    type: Product.type.CREDENTIAL,
    description: faker.lorem.lines(2),
    call_to_action: "Buy",
    price: 999,
    price_currency: "$",
    certificate_definitions: createDummyCertificateDefinition(),
  };
};
export const createDummyProducts = (number: number = 10): Product[] => {
  return [...Array(number)].map(() => createDummyProduct());
};
