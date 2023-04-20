import queryString from "query-string";
import { EntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { exportToFormData } from "@/utils/forms";

export const coursesRoute: EntityRoutesPaths = {
  get: (id: string, params: string = "") => `/courses/${id}/${params}`,
  getAll: (params: string = "") => `/courses/${params}`,
  create: "/courses/",
  update: (id: string) => `/courses/${id}/`,
  delete: (id: string) => `/courses/${id}/`,
};

interface Repository
  extends AbstractRepository<Course, ResourcesQuery, DTOCourse> {}

export const CourseRepository: Repository = class CourseRepository {
  static get(id: string, filters?: Maybe<ResourcesQuery>): Promise<Course> {
    const url = coursesRoute.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : ""
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(filters: Maybe<ResourcesQuery>): Promise<Course[]> {
    const url = coursesRoute.getAll(
      filters ? `?${queryString.stringify(filters)}` : ""
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }
  static create(payload: DTOCourse): Promise<Course> {
    return fetchApi(coursesRoute.create, {
      method: "POST",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(coursesRoute.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(id: string, payload: DTOCourse): Promise<Course> {
    return fetchApi(coursesRoute.update(id), {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }
};
