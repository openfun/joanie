import { defineMessages } from "react-intl";
import {
  ResourcesQuery,
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";
import { CertificateDefinitionRepository } from "@/services/repositories/certificate-definition/CertificateDefinitionRepository";

const messages = defineMessages({
  errorUpdate: {
    id: "hooks.useCertificateDefinitions.errorUpdate",
    description:
      "Error message shown to the user when certificate definition update request fails.",
    defaultMessage:
      "An error occurred while updating the certificate definition. Please retry later.",
  },
  errorGet: {
    id: "hooks.useCertificateDefinitions.errorSelect",
    description:
      "Error message shown to the user when certificate definitions fetch request fails.",
    defaultMessage:
      "An error occurred while fetching certificate definitions. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useCertificateDefinitions.errorDelete",
    description:
      "Error message shown to the user when certificate definition deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the certificate definition. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useCertificateDefinitions.errorCreate",
    description:
      "Error message shown to the user when certificate definition creation request fails.",
    defaultMessage:
      "An error occurred while creating the certificate definition. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useCertificateDefinitions.errorNotFound",
    description:
      "Error message shown to the user when no certificate definitions matches.",
    defaultMessage: "Cannot find the certificate definition",
  },
});

export type CertificateDefinitionResourceQuery = ResourcesQuery & {
  name?: string;
  template?: string;
};

/**
 * Joanie Api hook to retrieve/create/update/delete certificate definitions
 * owned by the authenticated user.
 */
const props: UseResourcesProps<
  CertificateDefinition,
  CertificateDefinitionResourceQuery
> = {
  queryKey: ["certificatesDefinitions"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return CertificateDefinitionRepository.get(id, otherFilters);
      } else {
        return CertificateDefinitionRepository.getAll(filters);
      }
    },
    create: CertificateDefinitionRepository.create,
    update: async ({ id, ...payload }) => {
      return CertificateDefinitionRepository.update(id, payload);
    },
    delete: async (id: string) => {
      return CertificateDefinitionRepository.delete(id);
    },
  }),
  omniscient: false,
  omniscientFiltering: (data, filters) => {
    return data.filter((todo) => {
      if (filters.name) {
        return todo.title.startsWith(filters.name);
      }
      return true;
    });
  },
  session: true,
  messages,
};
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useCertificateDefinitions = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useCertificateDefinition = useResource(props);
