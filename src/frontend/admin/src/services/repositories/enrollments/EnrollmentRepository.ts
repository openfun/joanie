import queryString from "query-string";
import { OrderQuery } from "@/services/api/models/Order";
import { Maybe } from "@/types/utils";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { PaginatedResponse } from "@/services/repositories/AbstractRepository";
import {
  DTOEnrollment,
  Enrollment,
  EnrollmentListItem,
} from "@/services/api/models/Enrollment";
import { exportToFormData } from "@/utils/forms";

export const enrollmentRoutes = {
  get: (id: string, params: string = "") => `/enrollments/${id}/${params}`,
  getAll: (params: string = "") => `/enrollments/${params}`,
  update: (id: string) => `/enrollments/${id}/`,
};

export class EnrollmentRepository {
  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<PaginatedResponse<EnrollmentListItem>> {
    const url = enrollmentRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static get(id: string, filters?: Maybe<OrderQuery>): Promise<Enrollment> {
    const url = enrollmentRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static update(
    id: string,
    payload?: Maybe<DTOEnrollment>,
  ): Promise<Enrollment> {
    const url = enrollmentRoutes.update(id);
    return fetchApi(url, {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }
}
