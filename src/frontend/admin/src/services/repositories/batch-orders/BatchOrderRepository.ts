import queryString from "query-string";
import { Maybe } from "@/types/utils";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { PaginatedResponse } from "@/types/api";
import { BatchOrder, BatchOrderQuery } from "@/services/api/models/BatchOrder";

export const batchOrderRoutes = {
  get: (id: string, params: string = "") => `/batch-orders/${id}/${params}`,
  getAll: (params: string = "") => `/batch-orders/${params}`,
  delete: (id: string) => `/batch-orders/${id}/`,
  confirmQuote: (id: string) => `/batch-orders/${id}/confirm-quote/`,
};

export class BatchOrderRepository {
  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<PaginatedResponse<BatchOrder>> {
    const url = batchOrderRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static get(
    id: string,
    filters?: Maybe<BatchOrderQuery>,
  ): Promise<BatchOrder> {
    const url = batchOrderRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    const url = batchOrderRoutes.delete(id);
    return fetchApi(url, { method: "DELETE" }).then(checkStatus);
  }

  static confirmQuote(id: string, total: string): Promise<BatchOrder> {
    const url = batchOrderRoutes.confirmQuote(id);
    return fetchApi(url, {
      method: "PATCH",
      body: JSON.stringify({ total }),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }
}
