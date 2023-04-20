import { faker } from "@faker-js/faker";
import { CertificationDefinition } from "@/services/api/models/CertificationDefinition";

export const createDummyCertificateDefinition = (): CertificationDefinition => {
  return {
    id: faker.datatype.uuid(),
    name: faker.datatype.string(30),
    template: "template.pdf",
    title: faker.company.name(),
    description: faker.lorem.lines(2),
  };
};

export const createDummyCertificatesDefinitions = (
  number: number = 10
): CertificationDefinition[] => {
  return [...Array(number)].map(() => createDummyCertificateDefinition());
};
