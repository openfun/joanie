import { faker } from "@faker-js/faker";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";

const build = () => {
  return {
    id: faker.datatype.uuid(),
    name: faker.datatype.string(30),
    template: "template.pdf",
    title: faker.company.name(),
    description: faker.lorem.lines(2),
  };
};

export function CertificateDefinitionFactory(): CertificateDefinition;
export function CertificateDefinitionFactory(
  count: number
): CertificateDefinition[];
export function CertificateDefinitionFactory(
  count?: number
): CertificateDefinition | CertificateDefinition[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
