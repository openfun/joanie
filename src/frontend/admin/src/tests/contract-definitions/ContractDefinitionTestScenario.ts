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

    let newContractDef: ContractDefinition;
    if (index >= 0) {
      newContractDef = { ...list[index], ...payload };
      list[index] = newContractDef;
    } else {
      newContractDef = { id: faker.string.uuid(), ...payload };
      list.push(newContractDef);
    }

    return newContractDef;
  };
  return {
    list,
    postUpdate,
  };
};
