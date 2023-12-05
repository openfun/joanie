import queryString from "query-string";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { exportToFormData } from "@/utils/forms";
import { DTOAccesses } from "@/services/api/models/Accesses";
import { SelectOption } from "@/components/presentational/hook-form/RHFSelect";
import { BaseEntityRoutesPaths } from "@/types/routes";

type OrganizationRoutes = BaseEntityRoutesPaths & {
  addUserAccess: (id: string) => string;
  updateUserAccess: (orgId: string, accessId: string) => string;
  removeUserAccess: (orgId: string, accessId: string) => string;
  options: string;
};

export const organizationRoute: OrganizationRoutes = {
  get: (id: string, params: string = "") => `/organizations/${id}/${params}`,
  getAll: (params: string = "") => `/organizations/${params}`,
  create: "/organizations/",
  options: "/organizations/",
  update: (id: string) => `/organizations/${id}/`,
  delete: (id: string) => `/organizations/${id}/`,
  addUserAccess: (id: string) => `/organizations/${id}/accesses/`,
  updateUserAccess: (orgId: string, accessId: string) =>
    `/organizations/${orgId}/accesses/${accessId}/`,
  removeUserAccess: (orgId: string, accessId: string) =>
    `/organizations/${orgId}/accesses/${accessId}/`,
};

interface Repository
  extends AbstractRepository<Organization, ResourcesQuery, DTOOrganization> {
  addUserAccess: (
    organizationId: string,
    userId: string,
    role: string,
  ) => Promise<void>;
  updateUserAccess: (
    orgId: string,
    accessId: string,
    payload: DTOAccesses,
  ) => Promise<void>;
  removeUserAccess: (orgId: string, accessId: string) => Promise<void>;
  getAvailableAccesses: () => Promise<SelectOption[]>;
}

export const OrganizationRepository: Repository = class OrganizationRepository {
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

  static addUserAccess(
    orgId: string,
    user: string,
    role: string,
  ): Promise<void> {
    return fetchApi(organizationRoute.addUserAccess(orgId), {
      method: "POST",
      body: exportToFormData({ user_id: user, role }),
    }).then(checkStatus);
  }

  static updateUserAccess(
    orgId: string,
    accessId: string,
    payload: DTOAccesses,
  ): Promise<void> {
    return fetchApi(organizationRoute.updateUserAccess(orgId, accessId), {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static removeUserAccess(orgId: string, accessId: string): Promise<void> {
    return fetchApi(organizationRoute.removeUserAccess(orgId, accessId), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static getAvailableAccesses(): Promise<SelectOption[]> {
    return fetchApi(organizationRoute.options, {
      method: "OPTIONS",
    }).then(async (response) => {
      const checkedResponse = await checkStatus(response);
      const result: { value: string; display_name: string }[] =
        checkedResponse.actions.POST.accesses.child.children.role.choices;
      return result.map(({ value, display_name: label }) => ({
        value,
        label,
      }));
    });
  }
};
