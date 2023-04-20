import queryString from "query-string";
import { EntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import {
  CertificationDefinition,
  DTOCertificationDefinition,
} from "@/services/api/models/CertificationDefinition";
import { exportToFormData } from "@/utils/forms";

export const certificateDefinitionRoutes: EntityRoutesPaths = {
  get: (id: string, params: string = "") =>
    `/certificate-definitions/${id}/${params}`,
  getAll: (params: string = "") => `/certificate-definitions/${params}`,
  create: "/certificate-definitions/",
  update: (id: string) => `/certificate-definitions/${id}/`,
  delete: (id: string) => `/certificate-definitions/${id}/`,
};

export const CertificateDefinitionRepository: AbstractRepository<
  CertificationDefinition,
  ResourcesQuery,
  DTOCertificationDefinition
> = class CertificateDefinitionRepository {
  static get(
    id: string,
    filters?: Maybe<ResourcesQuery>
  ): Promise<CertificationDefinition> {
    const url = certificateDefinitionRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : ""
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery>
  ): Promise<CertificationDefinition[]> {
    const url = certificateDefinitionRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : ""
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static create(
    payload: DTOCertificationDefinition
  ): Promise<CertificationDefinition> {
    return fetchApi(certificateDefinitionRoutes.create, {
      method: "POST",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(certificateDefinitionRoutes.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(
    id: string,
    payload: DTOCertificationDefinition
  ): Promise<CertificationDefinition> {
    return fetchApi(certificateDefinitionRoutes.update(id), {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }
};
