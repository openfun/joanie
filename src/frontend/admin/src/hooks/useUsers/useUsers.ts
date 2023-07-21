import { defineMessages } from "react-intl";
import {
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { UserRepository } from "@/services/repositories/Users/UsersRepository";
import { User } from "@/services/api/models/User";

export const useUsersMessages = defineMessages({
  errorUpdate: {
    id: "hooks.useUser.errorUpdate",
    description:
      "Error message shown to the user when user update request fails.",
    defaultMessage:
      "An error occurred while updating the user. Please retry later.",
  },
  errorGet: {
    id: "hooks.useUser.errorSelect",
    description:
      "Error message shown to the user when users fetch request fails.",
    defaultMessage:
      "An error occurred while fetching users. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useUser.errorDelete",
    description:
      "Error message shown to the user when user deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the user. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useUser.errorCreate",
    description:
      "Error message shown to the user when user creation request fails.",
    defaultMessage:
      "An error occurred while creating the user. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useUser.errorNotFound",
    description: "Error message shown to the user when no users matches.",
    defaultMessage: "Cannot find the user",
  },
});

/** const user = useUser();
 * Joanie Api hook to retrieve/create/update/delete courses
 * owned by the authenticated user.
 */
const props: UseResourcesProps<User> = {
  queryKey: ["users"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return UserRepository.get(id, otherFilters);
      } else {
        return UserRepository.getAll(filters);
      }
    },
    create: UserRepository.create,
    update: async ({ id, ...payload }) => {
      return UserRepository.update(id, payload);
    },
    delete: async (id?: string) => {
      if (id) {
        return UserRepository.delete(id);
      }
    },
  }),
  omniscient: false,
  session: true,
  messages: useUsersMessages,
};
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useUsers = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useUser = useResource(props);
