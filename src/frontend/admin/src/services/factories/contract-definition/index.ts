import { faker } from "@faker-js/faker";
import {
  ContractDefinition,
  ContractDefinitionTemplate,
} from "@/services/api/models/ContractDefinition";

const build = (): ContractDefinition => {
  return {
    id: faker.string.uuid(),
    title: faker.company.name(),
    description: faker.lorem.lines(2),
    language: "fr-fr",
    name: ContractDefinitionTemplate.DEFAULT,
    body: "### Contract body",
    appendix: "### Contract appendix",
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
