import { faker } from "@faker-js/faker";
import { QuoteDefinitionFactory } from "@/services/factories/quote-definition";
import {
  QuoteDefinition,
  DTOQuoteDefinition,
} from "@/services/api/models/QuoteDefinition";

export const getQuoteDefinitionScenarioStore = () => {
  const list = QuoteDefinitionFactory(5);

  const postUpdate = (
    payload: DTOQuoteDefinition,
    quoteDefinitionToUpdate?: QuoteDefinition,
  ) => {
    const index = list.findIndex(
      (item) => item.id === quoteDefinitionToUpdate?.id,
    );

    let newQuoteDef: QuoteDefinition;
    if (index >= 0) {
      newQuoteDef = { ...list[index], ...payload };
      list[index] = newQuoteDef;
    } else {
      newQuoteDef = { id: faker.string.uuid(), ...payload };
      list.push(newQuoteDef);
    }

    return newQuoteDef;
  };
  return {
    list,
    postUpdate,
  };
};
