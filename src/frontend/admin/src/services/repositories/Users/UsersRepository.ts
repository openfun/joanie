import queryString from "query-string";
import { EntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { exportToFormData } from "@/utils/forms";
import { User } from "@/services/api/models/User";

export const userRoutes: EntityRoutesPaths = {
  get: (id: string, params: string = "") => `/users/${id}/${params}`,
  getAll: (params: string = "") => `/users/${params}`,
  create: "/users/",
  update: (id: string) => `/users/${id}/`,
  delete: (id: string) => `/users/${id}/`,
};

interface Repository extends AbstractRepository<User, ResourcesQuery, User> {}

export const UserRepository: Repository = class UserRepository {
  static get(id: string, filters?: Maybe<ResourcesQuery>): Promise<User> {
    const url = userRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(filters: Maybe<ResourcesQuery>): Promise<User[]> {
    const url = userRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }
  static create(payload: User): Promise<User> {
    return fetchApi(userRoutes.create, {
      method: "POST",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(userRoutes.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(id: string, payload: User): Promise<User> {
    return fetchApi(userRoutes.update(id), {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }
};
