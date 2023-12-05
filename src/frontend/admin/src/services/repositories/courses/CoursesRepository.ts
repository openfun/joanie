import queryString from "query-string";
import { BaseEntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { exportToFormData } from "@/utils/forms";
import { DTOAccesses } from "@/services/api/models/Accesses";
import { SelectOption } from "@/components/presentational/hook-form/RHFSelect";
import { CourseRun } from "@/services/api/models/CourseRun";
import { CourseRunResourcesQuery } from "@/hooks/useCourseRun/useCourseRun";

export type CourseResourceQuery = ResourcesQuery & {
  state?: string;
  start?: string;
};

type CourseRoutes = BaseEntityRoutesPaths & {
  addUserAccess: (id: string) => string;
  updateUserAccess: (courseId: string, accessId: string) => string;
  removeUserAccess: (courseId: string, accessId: string) => string;
  getCoursesRuns: (courseId: string, params: string) => string;
  allRoles: string;
  options: string;
};

export const coursesRoute: CourseRoutes = {
  get: (id: string, params: string = "") => `/courses/${id}/${params}`,
  getAll: (params: string = "") => `/courses/${params}`,
  create: "/courses/",
  update: (id: string) => `/courses/${id}/`,
  delete: (id: string) => `/courses/${id}/`,
  getCoursesRuns: (courseId: string, params: string = "") =>
    `/courses/${courseId}/course-runs/${params}`,
  options: "/courses/",
  addUserAccess: (id: string) => `/courses/${id}/accesses/`,
  removeUserAccess: (courseId: string, accessId: string) =>
    `/courses/${courseId}/accesses/${accessId}/`,
  updateUserAccess: (courseId: string, accessId: string) =>
    `/courses/${courseId}/accesses/${accessId}/`,
  allRoles: "/courses/",
};

interface Repository
  extends AbstractRepository<Course, CourseResourceQuery, DTOCourse> {
  getCourseRuns: (
    courseId: string,
    filters?: Maybe<CourseRunResourcesQuery>,
  ) => Promise<CourseRun[]>;
  addUserAccess: (
    courseId: string,
    userId: string,
    role: string,
  ) => Promise<void>;
  updateUserAccess: (
    courseId: string,
    accessId: string,
    payload: DTOAccesses,
  ) => Promise<void>;
  removeUserAccess: (courseId: string, accessId: string) => Promise<void>;
  getAvailableAccesses: () => Promise<SelectOption[]>;
}

export const CourseRepository: Repository = class CourseRepository {
  static get(
    id: string,
    filters?: Maybe<CourseResourceQuery>,
  ): Promise<Course> {
    const url = coursesRoute.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(filters: Maybe<CourseResourceQuery>): Promise<Course[]> {
    const url = coursesRoute.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
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

  static getCourseRuns(
    courseId: string,
    filters: Maybe<CourseRunResourcesQuery>,
  ): Promise<CourseRun[]> {
    const url = coursesRoute.getCoursesRuns(
      courseId,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static addUserAccess(
    courseId: string,
    user: string,
    role: string,
  ): Promise<void> {
    return fetchApi(coursesRoute.addUserAccess(courseId), {
      method: "POST",
      body: exportToFormData({ user_id: user, role }),
    }).then(checkStatus);
  }

  static updateUserAccess(
    orgId: string,
    accessId: string,
    payload: DTOAccesses,
  ): Promise<void> {
    return fetchApi(coursesRoute.updateUserAccess(orgId, accessId), {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static removeUserAccess(courseId: string, accessId: string): Promise<void> {
    return fetchApi(coursesRoute.removeUserAccess(courseId, accessId), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static getAvailableAccesses(): Promise<SelectOption[]> {
    return fetchApi(coursesRoute.options, {
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
