import queryString from "query-string";
import { EntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { exportToFormData } from "@/utils/forms";

export const organizationRoute: EntityRoutesPaths = {
  get: (id: string, params: string = "") => `/organizations/${id}/${params}`,
  getAll: (params: string = "") => `/organizations/${params}`,
  create: "/organizations/",
  update: (id: string) => `/organizations/${id}/`,
  delete: (id: string) => `/organizations/${id}/`,
};

export const OrganizationRepository: AbstractRepository<
  Organization,
  ResourcesQuery,
  DTOOrganization
> = class OrganizationRepository {
  static get(
    id: string,
    filters?: Maybe<ResourcesQuery>,
  ): Promise<Organization> {
    const url = organizationRoute.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(filters: Maybe<ResourcesQuery>): Promise<Organization[]> {
    const url = organizationRoute.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }
  static create(payload: DTOOrganization): Promise<Organization> {
    return fetchApi(organizationRoute.create, {
      method: "POST",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(organizationRoute.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(id: string, payload: DTOOrganization): Promise<Organization> {
    return fetchApi(organizationRoute.update(id), {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }
};
