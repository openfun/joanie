import queryString from "query-string";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { DTOSkill, Skill } from "@/services/api/models/Skill";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { PaginatedResponse } from "@/types/api";
import { BaseEntityRoutesPaths } from "@/types/routes";
import {
  checkStatus,
  fetchApi,
  getAcceptLanguage,
} from "@/services/http/HttpService";
import { Maybe } from "@/types/utils";

const skillsRoute: BaseEntityRoutesPaths = {
  get: (id: Skill["id"], params = "") => `/skills/${id}/?${params}`,
  getAll: (params = "") => `/skills/?ordering=translations__title&${params}`,
  create: "/skills/",
  update: (id: Skill["id"]) => `/skills/${id}/`,
  delete: (id: Skill["id"]) => `/skills/${id}/`,
};

export const SkillRepository: AbstractRepository<
  Skill,
  ResourcesQuery,
  DTOSkill
> = class SkillRepository {
  static get(id: Skill["id"], filters: Maybe<ResourcesQuery> = {}) {
    const url = skillsRoute.get(id, queryString.stringify(filters));
    return fetchApi(url, {
      method: "GET",
      headers: { "Accept-Language": getAcceptLanguage() },
    }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery> = {},
  ): Promise<PaginatedResponse<Skill>> {
    const url = skillsRoute.getAll(queryString.stringify(filters));
    return fetchApi(url, {
      method: "GET",
      headers: {
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }

  static create(payload: DTOSkill): Promise<Skill> {
    return fetchApi(skillsRoute.create, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }

  static update(id: Skill["id"], payload: DTOSkill): Promise<Skill> {
    return fetchApi(skillsRoute.update(id), {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }

  static delete(id: Skill["id"]): Promise<void> {
    return fetchApi(skillsRoute.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }
};
