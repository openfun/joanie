import { defineMessages } from "react-intl";
import {
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { Product } from "@/services/api/models/Product";
import { ProductRepository } from "@/services/repositories/products/ProductRepository";

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
export const useProducts = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useProduct = useResource(props);
