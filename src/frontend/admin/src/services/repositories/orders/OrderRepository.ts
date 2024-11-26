import queryString from "query-string";
import { Order, OrderQuery } from "@/services/api/models/Order";
import { Maybe } from "@/types/utils";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { PaginatedResponse } from "@/types/api";

export const orderRoutes = {
  get: (id: string, params: string = "") => `/orders/${id}/${params}`,
  getAll: (params: string = "") => `/orders/${params}`,
  delete: (id: string) => `/orders/${id}/`,
  generateCertificate: (id: string) => `/orders/${id}/generate_certificate/`,
  refund: (id: string) => `/orders/${id}/refund/`,
};

export class OrderRepository {
  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<PaginatedResponse<Order>> {
    const url = orderRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static get(id: string, filters?: Maybe<OrderQuery>): Promise<Order> {
    const url = orderRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    const url = orderRoutes.delete(id);
    return fetchApi(url, { method: "DELETE" }).then(checkStatus);
  }

  static generateCertificate(id: string): Promise<void> {
    const url = orderRoutes.generateCertificate(id);
    return fetchApi(url, { method: "POST" }).then(checkStatus);
  }

  static refund(id: string): Promise<void> {
    const url = orderRoutes.refund(id);
    return fetchApi(url, { method: "POST" }).then(checkStatus);
  }
}
