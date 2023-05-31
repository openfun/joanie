import queryString from "query-string";
import { EntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import {
  checkStatus,
  fetchApi,
  getAcceptLanguage,
} from "@/services/http/HttpService";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import { JoanieLanguage } from "@/components/presentational/hook-form/RHFSelectLanguage";

export const coursesRunsRoute: EntityRoutesPaths = {
  get: (id: string, params: string = "") => `/course-runs/${id}/${params}`,
  getAll: (params: string = "") => `/course-runs/${params}`,
  create: "/course-runs/",
  update: (id: string) => `/course-runs/${id}/`,
  delete: (id: string) => `/course-runs/${id}/`,
};

interface Repository
  extends AbstractRepository<CourseRun, ResourcesQuery, DTOCourseRun> {
  getAllLanguages: () => Promise<JoanieLanguage[]>;
}

export const CoursesRunsRepository: Repository = class CoursesRunsRepository {
  static get(id: string, filters?: Maybe<ResourcesQuery>): Promise<CourseRun> {
    const url = coursesRunsRoute.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : ""
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(filters: Maybe<ResourcesQuery>): Promise<CourseRun[]> {
    const url = coursesRunsRoute.getAll(
      filters ? `?${queryString.stringify(filters)}` : ""
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }
  static create(payload: DTOCourseRun): Promise<CourseRun> {
    return fetchApi(coursesRunsRoute.create, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(coursesRunsRoute.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(id: string, payload: DTOCourseRun): Promise<CourseRun> {
    return fetchApi(coursesRunsRoute.update(id), {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }

  static getAllLanguages(): Promise<JoanieLanguage[]> {
    return fetchApi(coursesRunsRoute.getAll(), {
      method: "OPTIONS",
    }).then(async (response) => {
      const checkedResponse = await checkStatus(response);
      return checkedResponse.actions.POST.languages.choices;
    });
  }
};
