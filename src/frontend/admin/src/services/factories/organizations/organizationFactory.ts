import { faker } from "@faker-js/faker";
import { Organization } from "@/services/api/models/Organization";
import { createDummyFile } from "@/services/factories/files/fileFactory";

export const createDummyOrganization = (): Organization => {
  return {
    id: faker.datatype.uuid(),
    title: faker.company.name(),
    code: faker.company.companySuffix(),
    representative: faker.internet.email(),
    signature: createDummyFile(),
    logo: createDummyFile(),
  };
};

export const createDummyOrganizations = (
  number: number = 10
): Organization[] => {
  return [...Array(number)].map(() => createDummyOrganization());
};
