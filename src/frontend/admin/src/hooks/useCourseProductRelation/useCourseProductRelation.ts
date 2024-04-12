import { defineMessages, useIntl } from "react-intl";
import { useMutation } from "@tanstack/react-query";
import {
  QueryOptions,
  ResourcesQuery,
  useResource,
  useResourcesCustom,
  UseResourcesProps,
} from "@/hooks/useResources";
import { CourseProductRelationRepository } from "@/services/repositories/course-product-relation/CourseProductRelationRepository";
import { CourseProductRelation } from "@/services/api/models/Relations";
import { DTOOrderGroup } from "@/services/api/models/OrderGroup";

const messages = defineMessages({
  errorUpdate: {
    id: "hooks.useCourseProductRelation.errorUpdate",
    description:
      "Error message shown to the user when course product relation update request fails.",
    defaultMessage:
      "An error occurred while updating the course product relation. Please retry later.",
  },
  errorUpdateOrderGroup: {
    id: "hooks.useCourseProductRelation.errorUpdateOrderGroup",
    description:
      "Error message shown to the user when order group update request fails.",
    defaultMessage:
      "An error occurred while updating the order group. Please retry later.",
  },
  errorGet: {
    id: "hooks.useCourseProductRelation.errorGet",
    description:
      "Error message shown to the user when course product relations fetch request fails.",
    defaultMessage:
      "An error occurred while fetching course product relations. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useCourseProductRelation.errorDelete",
    description:
      "Error message shown to the user when course product relation deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the course product relation. Please retry later.",
  },
  errorDeleteOrderGroup: {
    id: "hooks.useCourseProductRelation.errorDeleteOrderGroup",
    description:
      "Error message shown to the user when order group deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the order group. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useCourseProductRelation.errorCreate",
    description:
      "Error message shown to the user when course product relation creation request fails.",
    defaultMessage:
      "An error occurred while creating the course product relation. Please retry later.",
  },
  errorCreateOrderGroup: {
    id: "hooks.useCourseProductRelation.errorCreateOrderGroup",
    description:
      "Error message shown to the user when order group creation request fails.",
    defaultMessage:
      "An error occurred while creating the order group. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useCourseProductRelation.errorNotFound",
    description:
      "Error message shown to the user when no course product relations matches.",
    defaultMessage: "Cannot find the course product relation",
  },
});

/**
 * Joanie Api hook to retrieve/create/update/delete course product relations
 * owned by the authenticated user.
 */
const props: UseResourcesProps<CourseProductRelation, ResourcesQuery> = {
  queryKey: ["course-product-relation"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return CourseProductRelationRepository.get(id, otherFilters);
      }

      return CourseProductRelationRepository.getAll(filters);
    },
    create: CourseProductRelationRepository.create,
    update: async ({ id, ...payload }) => {
      return CourseProductRelationRepository.update(id, payload);
    },
    delete: async (id: string) => {
      return CourseProductRelationRepository.delete(id);
    },
  }),
  session: true,
  messages,
};

export const useCourseProductRelations = (
  filters?: ResourcesQuery,
  queryOptions?: QueryOptions<CourseProductRelation>,
) => {
  const intl = useIntl();
  const custom = useResourcesCustom({ ...props, filters, queryOptions });
  const mutation = useMutation;

  return {
    ...custom,
    methods: {
      ...custom.methods,
      addOrderGroup: mutation({
        mutationFn: async (data: {
          relationId: string;
          payload: DTOOrderGroup;
        }) => {
          return CourseProductRelationRepository.addOrderGroup(
            data.relationId,
            data.payload,
          );
        },
        onSuccess: () => {
          custom.methods.invalidate();
        },
        onError: () => {
          custom.methods.setError(
            intl.formatMessage(messages.errorCreateOrderGroup),
          );
        },
      }).mutate,
      editOrderGroup: mutation({
        mutationFn: async (data: {
          relationId: string;
          orderGroupId: string;
          payload: DTOOrderGroup;
        }) => {
          return CourseProductRelationRepository.editOrderGroup(
            data.relationId,
            data.orderGroupId,
            data.payload,
          );
        },
        onSuccess: () => {
          custom.methods.invalidate();
        },
        onError: () => {
          custom.methods.setError(
            intl.formatMessage(messages.errorUpdateOrderGroup),
          );
        },
      }).mutate,
      deleteOrderGroup: mutation({
        mutationFn: async (data: {
          relationId: string;
          orderGroupId: string;
        }) => {
          return CourseProductRelationRepository.deleteOrderGroup(
            data.relationId,
            data.orderGroupId,
          );
        },
        onSuccess: () => {
          custom.methods.invalidate();
        },
        onError: () => {
          custom.methods.setError(
            intl.formatMessage(messages.errorDeleteOrderGroup),
          );
        },
      }).mutate,
    },
  };
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useCourseProductRelation = useResource(props);
