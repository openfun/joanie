import queryString from "query-string";
import { BaseEntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";

import { ResourcesQuery } from "@/hooks/useResources/types";
import { PaginatedResponse } from "@/types/api";
import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { DTOProduct, Product } from "@/services/api/models/Product";
import { exportToFormData } from "@/utils/forms";
import {
  DTOProductTargetCourseRelation,
  ProductTargetCourseRelation,
} from "@/services/api/models/ProductTargetCourseRelation";

type ProductRoutes = BaseEntityRoutesPaths & {
  createTargetCourseRelation: (productId: string) => string;
  editTargetCourseRelation: (productId: string, relationId: string) => string;
  reorderTargetCourses: (productId: string) => string;
};

export const productRoute: ProductRoutes = {
  get: (id: string, params: string = "") => `/products/${id}/${params}`,
  getAll: (params: string = "") => `/products/${params}`,
  create: "/products/",
  update: (id: string) => `/products/${id}/`,
  delete: (id: string) => `/products/${id}/`,
  createTargetCourseRelation: (productId: string) =>
    `/products/${productId}/target-courses/`,
  editTargetCourseRelation: (productId: string, relationId: string) =>
    `/products/${productId}/target-courses/${relationId}/`,
  reorderTargetCourses: (productId: string) =>
    `/products/${productId}/target-courses/reorder/`,
};

interface Repository
  extends AbstractRepository<Product, ResourcesQuery, DTOProduct> {
  addTargetCourse: (
    productId: string,
    payload: DTOProductTargetCourseRelation,
  ) => Promise<ProductTargetCourseRelation>;
  updateTargetCourse: (
    productId: string,
    relationId: string,
    payload: DTOProductTargetCourseRelation,
  ) => Promise<ProductTargetCourseRelation>;
  removeTargetCourse: (productId: string, relationId: string) => Promise<void>;
  reorderTargetCourses: (
    productId: string,
    reorderedIds: string[],
  ) => Promise<void>;
}

export const ProductRepository: Repository = class ProductRepository {
  static get(id: string, filters?: Maybe<ResourcesQuery>): Promise<Product> {
    const url = productRoute.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<PaginatedResponse<Product>> {
    const url = productRoute.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }
  static create(payload: DTOProduct): Promise<Product> {
    return fetchApi(productRoute.create, {
      method: "POST",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(productRoute.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(id: string, payload: DTOProduct): Promise<Product> {
    return fetchApi(productRoute.update(id), {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static addTargetCourse(
    productId: string,
    payload: DTOProductTargetCourseRelation,
  ): Promise<ProductTargetCourseRelation> {
    return fetchApi(productRoute.createTargetCourseRelation(productId), {
      method: "POST",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }
  static updateTargetCourse(
    productId: string,
    relationId: string,
    payload: DTOProductTargetCourseRelation,
  ): Promise<ProductTargetCourseRelation> {
    return fetchApi(
      productRoute.editTargetCourseRelation(productId, relationId),
      {
        method: "PATCH",
        body: exportToFormData(payload),
      },
    ).then(checkStatus);
  }

  static reorderTargetCourses(
    productId: string,
    reorderedIds: string[],
  ): Promise<void> {
    return fetchApi(productRoute.reorderTargetCourses(productId), {
      method: "POST",
      body: exportToFormData({ target_courses: reorderedIds }),
    }).then(checkStatus);
  }

  static removeTargetCourse(productId: string, relationId: string) {
    return fetchApi(
      productRoute.editTargetCourseRelation(productId, relationId),
      {
        method: "DELETE",
      },
    ).then(checkStatus);
  }
};
