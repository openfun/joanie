import { defineMessages, useIntl } from "react-intl";
import { useMutation } from "@tanstack/react-query";
import {
  QueryOptions,
  useResource,
  useResourcesCustom,
  UseResourcesProps,
} from "@/hooks/useResources";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { CourseProductRelationRepository } from "@/services/repositories/course-product-relation/CourseProductRelationRepository";
import { CourseProductRelation } from "@/services/api/models/Relations";
import { DTOOfferRule } from "@/services/api/models/OfferRule";

const messages = defineMessages({
  errorUpdate: {
    id: "hooks.useCourseProductRelation.errorUpdate",
    description:
      "Error message shown to the user when course product relation update request fails.",
    defaultMessage:
      "An error occurred while updating the course product relation. Please retry later.",
  },
  errorUpdateOfferRule: {
    id: "hooks.useCourseProductRelation.errorUpdateOfferRule",
    description:
      "Error message shown to the user when offer rule update request fails.",
    defaultMessage:
      "An error occurred while updating the offer rule. Please retry later.",
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
  errorDeleteOfferRule: {
    id: "hooks.useCourseProductRelation.errorDeleteOfferRule",
    description:
      "Error message shown to the user when offer rule deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the offer rule. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useCourseProductRelation.errorCreate",
    description:
      "Error message shown to the user when course product relation creation request fails.",
    defaultMessage:
      "An error occurred while creating the course product relation. Please retry later.",
  },
  errorCreateOfferRule: {
    id: "hooks.useCourseProductRelation.errorCreateOfferRule",
    description:
      "Error message shown to the user when offer rule creation request fails.",
    defaultMessage:
      "An error occurred while creating the offer rule. Please retry later.",
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
      addOfferRule: mutation({
        mutationFn: async (data: {
          relationId: string;
          payload: DTOOfferRule;
        }) => {
          return CourseProductRelationRepository.addOfferRule(
            data.relationId,
            data.payload,
          );
        },
        onSuccess: () => {
          custom.methods.invalidate();
        },
        onError: () => {
          custom.methods.setError(
            intl.formatMessage(messages.errorCreateOfferRule),
          );
        },
      }).mutate,
      editOfferRule: mutation({
        mutationFn: async (data: {
          relationId: string;
          offerRuleId: string;
          payload: DTOOfferRule;
        }) => {
          return CourseProductRelationRepository.editOfferRule(
            data.relationId,
            data.offerRuleId,
            data.payload,
          );
        },
        onSuccess: () => {
          custom.methods.invalidate();
        },
        onError: () => {
          custom.methods.setError(
            intl.formatMessage(messages.errorUpdateOfferRule),
          );
        },
      }).mutate,
      deleteOfferRule: mutation({
        mutationFn: async (data: {
          relationId: string;
          offerRuleId: string;
        }) => {
          return CourseProductRelationRepository.deleteOfferRule(
            data.relationId,
            data.offerRuleId,
          );
        },
        onSuccess: () => {
          custom.methods.invalidate();
        },
        onError: () => {
          custom.methods.setError(
            intl.formatMessage(messages.errorDeleteOfferRule),
          );
        },
      }).mutate,
    },
  };
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useCourseProductRelation = useResource(props);
