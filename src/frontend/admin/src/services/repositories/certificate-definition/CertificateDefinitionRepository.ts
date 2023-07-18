import queryString from "query-string";
import { EntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";

import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { exportToFormData } from "@/utils/forms";
import {
  CertificateDefinition,
  DTOCertificateDefinition,
} from "@/services/api/models/CertificateDefinition";
import { ResourcesQuery } from "@/hooks/useResources/types";

export const certificateDefinitionRoutes: EntityRoutesPaths = {
  get: (id: string, params: string = "") =>
    `/certificate-definitions/${id}/${params}`,
  getAll: (params: string = "") => `/certificate-definitions/${params}`,
  create: "/certificate-definitions/",
  update: (id: string) => `/certificate-definitions/${id}/`,
  delete: (id: string) => `/certificate-definitions/${id}/`,
};

export const CertificateDefinitionRepository: AbstractRepository<
  CertificateDefinition,
  ResourcesQuery,
  DTOCertificateDefinition
> = class CertificateDefinitionRepository {
  static get(
    id: string,
    filters?: Maybe<ResourcesQuery>,
  ): Promise<CertificateDefinition> {
    const url = certificateDefinitionRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<CertificateDefinition[]> {
    const url = certificateDefinitionRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static create(
    payload: DTOCertificateDefinition,
  ): Promise<CertificateDefinition> {
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
    payload: DTOCertificateDefinition,
  ): Promise<CertificateDefinition> {
    return fetchApi(certificateDefinitionRoutes.update(id), {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }
};
