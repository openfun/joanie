import queryString from "query-string";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { DTOTeacher, Teacher } from "@/services/api/models/Teacher";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { PaginatedResponse } from "@/types/api";
import { BaseEntityRoutesPaths } from "@/types/routes";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { Maybe } from "@/types/utils";

const teachersRoute: BaseEntityRoutesPaths = {
  get: (id: Teacher["id"], params = "") => `/teachers/${id}/?${params}`,
  getAll: (params = "") => `/teachers/?${params}`,
  create: "/teachers/",
  update: (id: Teacher["id"]) => `/teachers/${id}/`,
  delete: (id: Teacher["id"]) => `/teachers/${id}/`,
};

export const TeacherRepository: AbstractRepository<
  Teacher,
  ResourcesQuery,
  DTOTeacher
> = class TeacherRepository {
  static get(id: Teacher["id"], filters: Maybe<ResourcesQuery> = {}) {
    const url = teachersRoute.get(id, queryString.stringify(filters));
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery> = {},
  ): Promise<PaginatedResponse<Teacher>> {
    const url = teachersRoute.getAll(queryString.stringify(filters));
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static create(payload: DTOTeacher): Promise<Teacher> {
    return fetchApi(teachersRoute.create, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static update(id: Teacher["id"], payload: DTOTeacher): Promise<Teacher> {
    return fetchApi(teachersRoute.update(id), {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static delete(id: Teacher["id"]): Promise<void> {
    return fetchApi(teachersRoute.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }
};
