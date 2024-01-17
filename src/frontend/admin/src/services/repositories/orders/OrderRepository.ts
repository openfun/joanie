import queryString from "query-string";
import { Order, OrderQuery } from "@/services/api/models/Order";
import { Maybe } from "@/types/utils";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { checkStatus, fetchApi } from "@/services/http/HttpService";

export const orderRoutes = {
  get: (id: string, params: string = "") => `/orders/${id}/${params}`,
  getAll: (params: string = "") => `/orders/${params}`,
};

export class OrderRepository {
  static getAll(filters: Maybe<ResourcesQuery>): Promise<Order[]> {
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
}
