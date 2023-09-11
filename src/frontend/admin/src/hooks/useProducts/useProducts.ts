import { defineMessages, useIntl } from "react-intl";
import { useMutation } from "@tanstack/react-query";
import {
  QueryOptions,
  ResourcesQuery,
  useResource,
  useResourcesCustom,
  UseResourcesProps,
} from "@/hooks/useResources";
import { Product } from "@/services/api/models/Product";
import { ProductRepository } from "@/services/repositories/products/ProductRepository";
import { DTOProductTargetCourseRelation } from "@/services/api/models/ProductTargetCourseRelation";

const messages = defineMessages({
  errorUpdate: {
    id: "hooks.useProducts.errorUpdate",
    description:
      "Error message shown to the user when product update request fails.",
    defaultMessage:
      "An error occurred while updating the product. Please retry later.",
  },
  errorGet: {
    id: "hooks.useProducts.errorSelect",
    description:
      "Error message shown to the user when products fetch request fails.",
    defaultMessage:
      "An error occurred while fetching products. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useProducts.errorDelete",
    description:
      "Error message shown to the user when product deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the product. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useProducts.errorCreate",
    description:
      "Error message shown to the user when product creation request fails.",
    defaultMessage:
      "An error occurred while creating the product. Please retry later.",
  },
  errorCreateTargetCourses: {
    id: "hooks.useProducts.errorCreateTargetCourses",
    description:
      "Error message shown to the user when product target course relation creation request fails.",
    defaultMessage:
      "An error occurred while creating the product target course relation. Please retry later.",
  },
  errorDeleteTargetCourses: {
    id: "hooks.useProducts.errorDeleteTargetCourses",
    description:
      "Error message shown to the user when product target course relation delete request fails.",
    defaultMessage:
      "An error occurred while deleting the product target course relation. Please retry later.",
  },
  errorUpdateTargetCourses: {
    id: "hooks.useProducts.errorUpdateTargetCourses",
    description:
      "Error message shown to the user when product target course relation update request fails.",
    defaultMessage:
      "An error occurred while updating the product target course relation. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useProducts.errorNotFound",
    description: "Error message shown to the user when no products matches.",
    defaultMessage: "Cannot find the product",
  },
});

/** const certifs = useProducts();
 * Joanie Api hook to retrieve/create/update/delete products
 * owned by the authenticated user.
 */
const props: UseResourcesProps<Product> = {
  queryKey: ["products"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return ProductRepository.get(id, otherFilters);
      } else {
        return ProductRepository.getAll(filters);
      }
    },
    create: ProductRepository.create,
    update: async ({ id, ...payload }) => {
      return ProductRepository.update(id, payload);
    },
    delete: async (id: string) => {
      return ProductRepository.delete(id);
    },
  }),
  omniscient: false,
  session: true,
  messages,
};
// eslint-disable-next-line react-hooks/rules-of-hooks

export const useProducts = (
  filters?: ResourcesQuery,
  queryOptions?: QueryOptions<Product>,
) => {
  const intl = useIntl();
  const custom = useResourcesCustom({ ...props, filters, queryOptions });
  const mutation = useMutation;

  return {
    ...custom,
    methods: {
      ...custom.methods,
      addTargetCourse: mutation(
        async (data: {
          productId: string;
          payload: DTOProductTargetCourseRelation;
        }) => {
          return ProductRepository.addTargetCourse(
            data.productId,
            data.payload,
          );
        },
        {
          onSuccess: () => {
            custom.methods.invalidate();
          },
          onError: () => {
            custom.methods.setError(
              intl.formatMessage(messages.errorCreateTargetCourses),
            );
          },
        },
      ).mutate,
      removeTargetCourse: mutation(
        async (data: { productId: string; relationId: string }) => {
          return ProductRepository.removeTargetCourse(
            data.productId,
            data.relationId,
          );
        },
        {
          onSuccess: () => {
            custom.methods.invalidate();
          },
          onError: () => {
            custom.methods.setError(
              intl.formatMessage(messages.errorUpdateTargetCourses),
            );
          },
        },
      ).mutate,
      updateTargetCourse: mutation(
        async (data: {
          productId: string;
          relationId: string;
          payload: DTOProductTargetCourseRelation;
        }) => {
          return ProductRepository.updateTargetCourse(
            data.productId,
            data.relationId,
            data.payload,
          );
        },
        {
          onSuccess: () => {
            custom.methods.invalidate();
          },
          onError: () => {
            custom.methods.setError(
              intl.formatMessage(messages.errorUpdateTargetCourses),
            );
          },
        },
      ).mutate,
      reorderTargetCourses: mutation(
        async (data: { productId: string; target_courses: string[] }) => {
          return ProductRepository.reorderTargetCourses(
            data.productId,
            data.target_courses,
          );
        },
        {
          onSuccess: () => {
            custom.methods.invalidate();
          },
          onError: () => {
            custom.methods.setError(
              intl.formatMessage(messages.errorUpdateTargetCourses),
            );
          },
        },
      ).mutate,
    },
  };
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useProduct = useResource(props);
