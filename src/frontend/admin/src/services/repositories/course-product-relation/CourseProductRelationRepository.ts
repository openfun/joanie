import queryString from "query-string";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import {
  checkStatus,
  fetchApi,
  getAcceptLanguage,
} from "@/services/http/HttpService";
import {
  CourseProductRelation,
  DTOCourseProductRelation,
} from "@/services/api/models/Relations";
import { DTOOrderGroup, OrderGroup } from "@/services/api/models/OrderGroup";
import { exportToFormData } from "@/utils/forms";
import { PaginatedResponse } from "@/services/repositories/AbstractRepository";

export const courseProductRelationsRoutes = {
  getAll: (params: string = "") => `/course-product-relations/${params}`,
  create: `/course-product-relations/`,
  get: (id: string, params: string = "") =>
    `/course-product-relations/${id}/${params}`,
  update: (id: string) => `/course-product-relations/${id}/`,
  delete: (id: string) => `/course-product-relations/${id}/`,
  addOrderGroup: (id: string) =>
    `/course-product-relations/${id}/order-groups/`,
  editOrderGroup: (id: string, orderGroupId: string) =>
    `/course-product-relations/${id}/order-groups/${orderGroupId}/`,
  deleteOrderGroup: (id: string, orderGroupId: string) =>
    `/course-product-relations/${id}/order-groups/${orderGroupId}/`,
};

export const CourseProductRelationRepository = class CourseProductRelationRepository {
  static get(
    id: string,
    filters?: Maybe<ResourcesQuery>,
  ): Promise<CourseProductRelation> {
    const url = courseProductRelationsRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<PaginatedResponse<CourseProductRelation>> {
    const url = courseProductRelationsRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static create(
    payload: DTOCourseProductRelation,
  ): Promise<CourseProductRelation> {
    return fetchApi(courseProductRelationsRoutes.create, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(courseProductRelationsRoutes.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(
    id: string,
    payload: DTOCourseProductRelation,
  ): Promise<CourseProductRelation> {
    return fetchApi(courseProductRelationsRoutes.update(id), {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }

  static addOrderGroup(
    relationId: string,
    orderGroup: DTOOrderGroup,
  ): Promise<OrderGroup> {
    return fetchApi(courseProductRelationsRoutes.addOrderGroup(relationId), {
      method: "POST",
      body: exportToFormData(orderGroup),
    }).then(checkStatus);
  }

  static editOrderGroup(
    relationId: string,
    orderGroupId: string,
    orderGroup: DTOOrderGroup,
  ): Promise<OrderGroup> {
    return fetchApi(
      courseProductRelationsRoutes.editOrderGroup(relationId, orderGroupId),
      {
        method: "PATCH",
        body: exportToFormData(orderGroup),
      },
    ).then(checkStatus);
  }
  static deleteOrderGroup(
    relationId: string,
    orderGroupId: string,
  ): Promise<OrderGroup> {
    return fetchApi(
      courseProductRelationsRoutes.deleteOrderGroup(relationId, orderGroupId),
      {
        method: "DELETE",
      },
    ).then(checkStatus);
  }
};
