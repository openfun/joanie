import queryString from "query-string";
import { Maybe } from "@/types/utils";
import { ResourcesQuery } from "@/hooks/useResources/types";
import {
  buildApiUrl,
  checkStatus,
  fetchApi,
} from "@/services/http/HttpService";
import { PaginatedResponse } from "@/types/api";
import { BatchOrder, BatchOrderQuery } from "@/services/api/models/BatchOrder";

export const batchOrderRoutes = {
  get: (id: string, params: string = "") => `/batch-orders/${id}/${params}`,
  getAll: (params: string = "") => `/batch-orders/${params}`,
  delete: (id: string) => `/batch-orders/${id}/`,
  confirmQuote: (id: string) => `/batch-orders/${id}/confirm-quote/`,
  confirmPurchaseOrder: (id: string) =>
    `/batch-orders/${id}/confirm-purchase-order/`,
  confirmBankTransfer: (id: string) =>
    `/batch-orders/${id}/confirm-bank-transfer/`,
  submitForSignature: (id: string) =>
    `/batch-orders/${id}/submit-for-signature/`,
  generateOrders: (id: string) => `/batch-orders/${id}/generate-orders/`,
  export: (params: string = "") => `/batch-orders/export/${params}`,
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

  static confirmPurchaseOrder(id: string): Promise<BatchOrder> {
    const url = batchOrderRoutes.confirmPurchaseOrder(id);
    return fetchApi(url, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static confirmBankTransfer(id: string): Promise<BatchOrder> {
    const url = batchOrderRoutes.confirmBankTransfer(id);
    return fetchApi(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static submitForSignature(id: string): Promise<BatchOrder> {
    const url = batchOrderRoutes.submitForSignature(id);
    return fetchApi(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static generateOrders(id: string): Promise<BatchOrder> {
    const url = batchOrderRoutes.generateOrders(id);
    return fetchApi(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static export(filters: Maybe<ResourcesQuery>): void {
    const url = batchOrderRoutes.export(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    window.open(buildApiUrl(url));
  }
}
