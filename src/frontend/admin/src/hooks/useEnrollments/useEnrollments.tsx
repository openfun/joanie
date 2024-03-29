import { defineMessages } from "react-intl";
import {
  ResourcesQuery,
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { EnrollmentRepository } from "@/services/repositories/enrollments/EnrollmentRepository";
import {
  Enrollment,
  EnrollmentListItem,
} from "@/services/api/models/Enrollment";

export const useEnrollmentsMessages = defineMessages({
  errorUpdate: {
    id: "hooks.useEnrollments.errorUpdate",
    description:
      "Error message shown to the user when order update request fails.",
    defaultMessage:
      "An error occurred while updating the order. Please retry later.",
  },
  errorGet: {
    id: "hooks.useEnrollments.errorGet",
    description:
      "Error message shown to the user when orders fetch request fails.",
    defaultMessage:
      "An error occurred while fetching orders. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useEnrollments.errorDelete",
    description:
      "Error message shown to the user when order deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the order. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useEnrollments.errorCreate",
    description:
      "Error message shown to the user when order creation request fails.",
    defaultMessage:
      "An error occurred while creating the order. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useEnrollments.errorNotFound",
    description: "Error message shown to the user when no order matches.",
    defaultMessage: "Cannot find the order",
  },
});

export type EnrollmentsListQuery = ResourcesQuery & {
  course_run_ids?: string[];
  is_active?: boolean;
  state?: string;
  user_ids?: string[];
};

const listProps: UseResourcesProps<EnrollmentListItem, EnrollmentsListQuery> = {
  queryKey: ["enrollmentsList"],
  apiInterface: () => ({
    get: async (filters) => {
      return EnrollmentRepository.getAll(filters);
    },
  }),
  session: true,
  messages: useEnrollmentsMessages,
};

export type EnrollmentQuery = ResourcesQuery & {};

const enrollmentProps: UseResourcesProps<Enrollment, EnrollmentQuery> = {
  queryKey: ["enrollments"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return EnrollmentRepository.get(id, otherFilters);
      }
    },
    update: async ({ id, ...payload }) => {
      return EnrollmentRepository.update(id, payload);
    },
  }),
  session: true,
  messages: useEnrollmentsMessages,
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useEnrollments = useResources(listProps);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useEnrollment = useResource(enrollmentProps);
