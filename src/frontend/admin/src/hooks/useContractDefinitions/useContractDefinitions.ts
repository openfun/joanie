import { defineMessages } from "react-intl";
import {
  ResourcesQuery,
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { ContractDefinitionRepository } from "@/services/repositories/contract-definition/ContractDefinitionRepository";
import { ContractDefinition } from "@/services/api/models/ContractDefinition";

const messages = defineMessages({
  errorUpdate: {
    id: "hooks.useContractDefinitions.errorUpdate",
    description:
      "Error message shown to the user when contract definition update request fails.",
    defaultMessage:
      "An error occurred while updating the contract definition. Please retry later.",
  },
  errorGet: {
    id: "hooks.useContractDefinitions.errorSelect",
    description:
      "Error message shown to the user when contract definitions fetch request fails.",
    defaultMessage:
      "An error occurred while fetching contract definitions. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useContractDefinitions.errorDelete",
    description:
      "Error message shown to the user when contract definition deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the contract definition. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useContractDefinitions.errorCreate",
    description:
      "Error message shown to the user when contract definition creation request fails.",
    defaultMessage:
      "An error occurred while creating the contract definition. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useContractDefinitions.errorNotFound",
    description:
      "Error message shown to the user when no contract definitions matches.",
    defaultMessage: "Cannot find the contract definition",
  },
});

export type ContractDefinitionResourceQuery = ResourcesQuery & {
  name?: string;
  language?: string;
};

/**
 * Joanie Api hook to retrieve/create/update/delete contract definitions
 * owned by the authenticated user.
 */
const props: UseResourcesProps<
  ContractDefinition,
  ContractDefinitionResourceQuery
> = {
  queryKey: ["contractDefinitions"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return ContractDefinitionRepository.get(id, otherFilters);
      } else {
        return ContractDefinitionRepository.getAll(filters);
      }
    },
    create: ContractDefinitionRepository.create,
    update: async ({ id, ...payload }) => {
      return ContractDefinitionRepository.update(id, payload);
    },
    delete: async (id: string) => {
      return ContractDefinitionRepository.delete(id);
    },
  }),
  session: true,
  messages,
};
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useContractDefinitions = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useContractDefinition = useResource(props);
