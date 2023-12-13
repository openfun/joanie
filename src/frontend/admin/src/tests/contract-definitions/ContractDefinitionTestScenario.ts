import { faker } from "@faker-js/faker";
import { ContractDefinitionFactory } from "@/services/factories/contract-definition";
import {
  ContractDefinition,
  DTOContractDefinition,
} from "@/services/api/models/ContractDefinition";

export const getContractDefinitionScenarioStore = () => {
  const list = ContractDefinitionFactory(5);

  const postUpdate = (
    payload: DTOContractDefinition,
    contractDefinitionToUpdate?: ContractDefinition,
  ) => {
    const index = list.findIndex(
      (item) => item.id === contractDefinitionToUpdate?.id,
    );

    let newCertificationDef: ContractDefinition;
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
