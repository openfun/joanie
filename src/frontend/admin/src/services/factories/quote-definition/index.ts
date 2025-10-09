import { faker } from "@faker-js/faker";
import {
  QuoteDefinition,
  QuoteDefinitionTemplate,
} from "@/services/api/models/QuoteDefinition";

const build = (): QuoteDefinition => {
  return {
    id: faker.string.uuid(),
    title: faker.company.name(),
    description: faker.lorem.lines(2),
    language: "fr-fr",
    name: QuoteDefinitionTemplate.DEFAULT,
    body: "### Quote body",
  };
};

export function QuoteDefinitionFactory(): QuoteDefinition;
export function QuoteDefinitionFactory(count: number): QuoteDefinition[];
export function QuoteDefinitionFactory(
  count?: number,
): QuoteDefinition | QuoteDefinition[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
