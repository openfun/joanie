import queryString from "query-string";
import { Maybe } from "@/types/utils";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { PaginatedResponse } from "@/types/api";
import { BatchOrder } from "@/services/api/models/BatchOrder";

export const batchOrderRoutes = {
  getAll: (params: string = "") => `/batch-orders/${params}`,
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
}
