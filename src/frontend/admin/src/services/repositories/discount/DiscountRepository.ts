import queryString from "query-string";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { PaginatedResponse } from "@/types/api";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { Discount, DTODiscount } from "@/services/api/models/Discount";
import { BaseEntityRoutesPaths } from "@/types/routes";

type DiscountRoutes = BaseEntityRoutesPaths;

export const discountRoutes: DiscountRoutes = {
  get: (id: string, params: string = "") => `/discounts/${id}/${params}`,
  getAll: (params: string = "") => `/discounts/${params}`,
  create: "/discounts/",
  update: (id: string) => `/discounts/${id}/`,
  delete: (id: string) => `/discounts/${id}/`,
};

interface Repository
  extends AbstractRepository<Discount, ResourcesQuery, DTODiscount> {}

export const DiscountRepository: Repository = class DiscountRepository {
  static get(id: string, filters?: Maybe<ResourcesQuery>): Promise<Discount> {
    const url = discountRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<PaginatedResponse<Discount>> {
    const url = discountRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static create(payload: DTODiscount): Promise<Discount> {
    return fetchApi(discountRoutes.create, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(discountRoutes.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(id: string, payload: DTODiscount): Promise<Discount> {
    return fetchApi(discountRoutes.update(id), {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }
};
