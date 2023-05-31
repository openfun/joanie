import { faker } from "@faker-js/faker";
import { Product, ProductType } from "@/services/api/models/Product";
import { CertificateDefinitionFactory } from "@/services/factories/certificate-definition";

const build = (): Product => {
  return {
    id: faker.datatype.uuid(),
    title: faker.company.name(),
    type: ProductType.CREDENTIAL,
    description: faker.lorem.lines(2),
    call_to_action: "Buy",
    price: 999,
    price_currency: "$",
    certificate_definitions: CertificateDefinitionFactory(),
  };
};

export function ProductFactory(): Product;
export function ProductFactory(count: number): Product[];
export function ProductFactory(count?: number): Product | Product[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
