import { defineMessages } from "react-intl";
import {
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { Organization } from "@/services/api/models/Organization";
import { OrganizationRepository } from "@/services/repositories/organization/OrganizationRepository";

export const useOrganizationsMessages = defineMessages({
  errorUpdate: {
    id: "hooks.useOrganizations.errorUpdate",
    description:
      "Error message shown to the user when organization update request fails.",
    defaultMessage:
      "An error occurred while updating the organization. Please retry later.",
  },
  errorGet: {
    id: "hooks.useOrganizations.errorSelect",
    description:
      "Error message shown to the user when organizations fetch request fails.",
    defaultMessage:
      "An error occurred while fetching organizations. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useOrganizations.errorDelete",
    description:
      "Error message shown to the user when organization deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the organization. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useOrganizations.errorCreate",
    description:
      "Error message shown to the user when organization creation request fails.",
    defaultMessage:
      "An error occurred while creating the organization. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useOrganizations.errorNotFound",
    description:
      "Error message shown to the user when no organization matches.",
    defaultMessage: "Cannot find the organization",
  },
});

/** const certifs = useOrganizations();
 * Joanie Api hook to retrieve/create/update/delete organizations
 * owned by the authenticated user.
 */
const props: UseResourcesProps<Organization> = {
  queryKey: ["organizations"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return OrganizationRepository.get(id, otherFilters);
      } else {
        return OrganizationRepository.getAll(filters);
      }
    },
    create: OrganizationRepository.create,
    update: async ({ id, ...payload }) => {
      return OrganizationRepository.update(id, payload);
    },
    delete: async (id: string) => {
      return OrganizationRepository.delete(id);
    },
  }),
  omniscient: false,
  session: true,
  messages: useOrganizationsMessages,
};
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useOrganizations = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useOrganization = useResource(props);
