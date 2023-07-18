import queryString from "query-string";
import { EntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { Product } from "@/services/api/models/Product";

export const productRoute: EntityRoutesPaths = {
  get: (id: string, params: string = "") => `/products/${id}/${params}`,
  getAll: (params: string = "") => `/products/${params}`,
  create: "/products/",
  update: (id: string) => `/products/${id}/`,
  delete: (id: string) => `/products/${id}/`,
};

export const ProductRepository: AbstractRepository<
  Product,
  ResourcesQuery,
  Product
> = class OrganizationRepository {
  static get(id: string, filters?: Maybe<ResourcesQuery>): Promise<Product> {
    const url = productRoute.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(filters: Maybe<ResourcesQuery>): Promise<Product[]> {
    const url = productRoute.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }
  static create(payload: Partial<Product>): Promise<Product> {
    return fetchApi(productRoute.create, {
      method: "POST",
      body: JSON.stringify(payload),
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(productRoute.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(id: string, payload: Partial<Product>): Promise<Product> {
    return fetchApi(productRoute.update(id), {
      method: "PATCH",
      body: JSON.stringify(payload),
    }).then(checkStatus);
  }
};
