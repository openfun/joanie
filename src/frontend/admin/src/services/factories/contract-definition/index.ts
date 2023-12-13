import { faker } from "@faker-js/faker";
import { ContractDefinition } from "@/services/api/models/ContractDefinition";

const build = (): ContractDefinition => {
  return {
    id: faker.string.uuid(),
    title: faker.company.name(),
    description: faker.lorem.lines(2),
    language: "fr-fr",
    name: "contract_definition",
    body: "### Contract body",
  };
};

export function ContractDefinitionFactory(): ContractDefinition;
export function ContractDefinitionFactory(count: number): ContractDefinition[];
export function ContractDefinitionFactory(
  count?: number,
): ContractDefinition | ContractDefinition[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
