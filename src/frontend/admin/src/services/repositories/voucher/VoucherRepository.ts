import queryString from "query-string";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { PaginatedResponse } from "@/types/api";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { Voucher, DTOVoucher } from "@/services/api/models/Voucher";
import { BaseEntityRoutesPaths } from "@/types/routes";

type VoucherRoutes = BaseEntityRoutesPaths;

export const voucherRoutes: VoucherRoutes = {
  get: (id: string, params: string = "") => `/vouchers/${id}/${params}`,
  getAll: (params: string = "") => `/vouchers/${params}`,
  create: "/vouchers/",
  update: (id: string) => `/vouchers/${id}/`,
  delete: (id: string) => `/vouchers/${id}/`,
};

interface Repository extends AbstractRepository<
  Voucher,
  ResourcesQuery,
  DTOVoucher
> {}

export const VoucherRepository: Repository = class VoucherRepository {
  static get(id: string, filters?: Maybe<ResourcesQuery>): Promise<Voucher> {
    const url = voucherRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<PaginatedResponse<Voucher>> {
    const url = voucherRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static create(payload: DTOVoucher): Promise<Voucher> {
    return fetchApi(voucherRoutes.create, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(voucherRoutes.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(id: string, payload: DTOVoucher): Promise<Voucher> {
    return fetchApi(voucherRoutes.update(id), {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }
};
