import { defineMessages } from "react-intl";
import {
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { QuoteDefinitionRepository } from "@/services/repositories/quote-definition/QuoteDefinitionRepository";
import { QuoteDefinition } from "@/services/api/models/QuoteDefinition";

const messages = defineMessages({
  errorUpdate: {
    id: "hooks.useQuoteDefinitions.errorUpdate",
    description:
      "Error message shown to the user when quote definition update request fails.",
    defaultMessage:
      "An error occurred while updating the quote definition. Please retry later.",
  },
  errorGet: {
    id: "hooks.useQuoteDefinitions.errorSelect",
    description:
      "Error message shown to the user when quote definitions fetch request fails.",
    defaultMessage:
      "An error occurred while fetching quote definitions. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useQuoteDefinitions.errorDelete",
    description:
      "Error message shown to the user when quote definition deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the quote definition. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useQuoteDefinitions.errorCreate",
    description:
      "Error message shown to the user when quote definition creation request fails.",
    defaultMessage:
      "An error occurred while creating the quote definition. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useQuoteDefinitions.errorNotFound",
    description:
      "Error message shown to the user when no quote definitions matches.",
    defaultMessage: "Cannot find the quote definition",
  },
});

export type QuoteDefinitionResourceQuery = ResourcesQuery & {
  name?: string;
  language?: string;
};

/**
 * Joanie Api hook to retrieve/create/update/delete quote definitions.
 */
const props: UseResourcesProps<QuoteDefinition, QuoteDefinitionResourceQuery> =
  {
    queryKey: ["quoteDefinitions"],
    apiInterface: () => ({
      get: async (filters) => {
        if (filters?.id) {
          const { id, ...otherFilters } = filters;
          return QuoteDefinitionRepository.get(id, otherFilters);
        } else {
          return QuoteDefinitionRepository.getAll(filters);
        }
      },
      create: QuoteDefinitionRepository.create,
      update: async ({ id, ...payload }) => {
        return QuoteDefinitionRepository.update(id, payload);
      },
      delete: async (id: string) => {
        return QuoteDefinitionRepository.delete(id);
      },
    }),
    session: true,
    messages,
  };
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useQuoteDefinitions = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useQuoteDefinition = useResource(props);
