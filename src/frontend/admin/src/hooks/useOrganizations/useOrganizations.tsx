import { defineMessages, useIntl } from "react-intl";
import { useQuery } from "@tanstack/react-query";
import {
  QueryOptions,
  ResourcesQuery,
  useResource,
  useResourcesCustom,
  UseResourcesProps,
} from "@/hooks/useResources";
import { Organization } from "@/services/api/models/Organization";
import { OrganizationRepository } from "@/services/repositories/organization/OrganizationRepository";
import { DTOAccesses } from "@/services/api/models/Accesses";
import { SelectOption } from "@/components/presentational/hook-form/RHFSelect";

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

export const useOrganizations = (
  filters?: ResourcesQuery,
  queryOptions?: QueryOptions<Organization>,
) => {
  const intl = useIntl();
  const custom = useResourcesCustom({ ...props, filters, queryOptions });
  const accesses = useAllOrganizationAccesses();
  return {
    ...custom,
    accesses,
    methods: {
      ...custom.methods,
      addAccessUser: async (orgId: string, user: string, role: string) => {
        try {
          const result = await OrganizationRepository.addUserAccess(
            orgId,
            user,
            role,
          );
          await custom.methods.invalidate();
          return result;
        } catch (e) {
          custom.methods.setError(
            intl.formatMessage(useOrganizationsMessages.errorCreate),
          );
        }
      },
      updateAccessUser: async (
        orgId: string,
        accessId: string,
        payload: DTOAccesses,
      ) => {
        try {
          await OrganizationRepository.updateUserAccess(
            orgId,
            accessId,
            payload,
          );
          await custom.methods.invalidate();
        } catch (e) {
          custom.methods.setError(
            intl.formatMessage(useOrganizationsMessages.errorUpdate),
          );
        }
      },
      removeAccessUser: async (orgId: string, accessId: string) => {
        try {
          await OrganizationRepository.removeUserAccess(orgId, accessId);
          await custom.methods.invalidate();
        } catch (e) {
          custom.methods.setError(
            intl.formatMessage(useOrganizationsMessages.errorDelete),
          );
        }
      },
    },
  };
};

// eslint-disable-next-line react-hooks/rules-of-hooks
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useOrganization = useResource(props);

export const useAllOrganizationAccesses = (): SelectOption[] | undefined => {
  const accesses = useQuery({
    queryKey: ["allOrganizationAccesses"],
    queryFn: async () => {
      return OrganizationRepository.getAvailableAccesses();
    },
    staleTime: Infinity,
    gcTime: Infinity,
  });

  return accesses?.data ?? undefined;
};
