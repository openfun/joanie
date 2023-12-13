import { faker } from "@faker-js/faker";
import { CertificateDefinitionFactory } from "@/services/factories/certificate-definition";
import {
  CertificateDefinition,
  DTOCertificateDefinition,
} from "@/services/api/models/CertificateDefinition";

export const getCertificateDefinitionScenarioStore = (
  itemsNumber: number = 30,
) => {
  const list = CertificateDefinitionFactory(itemsNumber);

  const postUpdate = (
    payload: DTOCertificateDefinition,
    certificationDefinitionToUpdate?: CertificateDefinition,
  ) => {
    const index = list.findIndex(
      (item) => item.id === certificationDefinitionToUpdate?.id,
    );

    let newCertificationDef: CertificateDefinition;
    if (index >= 0) {
      newCertificationDef = { ...list[index], ...payload };
      list[index] = newCertificationDef;
    } else {
      newCertificationDef = { id: faker.string.uuid(), ...payload };
      list.push(newCertificationDef);
    }

    return newCertificationDef;
  };
  return {
    list,
    postUpdate,
  };
};
