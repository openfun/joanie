import queryString from "query-string";
import { BaseEntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";

import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { exportToFormData } from "@/utils/forms";
import {
  ContractDefinition,
  DTOContractDefinition,
} from "@/services/api/models/ContractDefinition";
import { ResourcesQuery } from "@/hooks/useResources/types";

export const contractDefinitionRoutes: BaseEntityRoutesPaths = {
  get: (id: string, params: string = "") =>
    `/contract-definitions/${id}/${params}`,
  getAll: (params: string = "") => `/contract-definitions/${params}`,
  create: "/contract-definitions/",
  update: (id: string) => `/contract-definitions/${id}/`,
  delete: (id: string) => `/contract-definitions/${id}/`,
};

export const ContractDefinitionRepository: AbstractRepository<
  ContractDefinition,
  ResourcesQuery,
  DTOContractDefinition
> = class ContractDefinitionRepository {
  static get(
    id: string,
    filters?: Maybe<ResourcesQuery>,
  ): Promise<ContractDefinition> {
    const url = contractDefinitionRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(filters: Maybe<ResourcesQuery>): Promise<ContractDefinition[]> {
    const url = contractDefinitionRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static create(payload: DTOContractDefinition): Promise<ContractDefinition> {
    return fetchApi(contractDefinitionRoutes.create, {
      method: "POST",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(contractDefinitionRoutes.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(
    id: string,
    payload: DTOContractDefinition,
  ): Promise<ContractDefinition> {
    return fetchApi(contractDefinitionRoutes.update(id), {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }
};
