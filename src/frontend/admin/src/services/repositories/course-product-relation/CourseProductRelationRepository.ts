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
import { DTOOfferRule, OfferRule } from "@/services/api/models/OfferRule";
import { exportToFormData } from "@/utils/forms";
import { PaginatedResponse } from "@/types/api";

export const courseProductRelationsRoutes = {
  getAll: (params: string = "") => `/course-product-relations/${params}`,
  create: `/course-product-relations/`,
  get: (id: string, params: string = "") =>
    `/course-product-relations/${id}/${params}`,
  update: (id: string) => `/course-product-relations/${id}/`,
  delete: (id: string) => `/course-product-relations/${id}/`,
  addOfferRule: (id: string) => `/course-product-relations/${id}/offer-rules/`,
  editOfferRule: (id: string, offerRuleId: string) =>
    `/course-product-relations/${id}/offer-rules/${offerRuleId}/`,
  deleteOfferRule: (id: string, offerRuleId: string) =>
    `/course-product-relations/${id}/offer-rules/${offerRuleId}/`,
  checkCertificateGeneration: (id: string) =>
    `/course-product-relations/${id}/check_certificates_generation_process/`,

  generateMultipleCertificate: (id: string) =>
    `/course-product-relations/${id}/generate_certificates/`,
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

  static addOfferRule(
    relationId: string,
    offerRule: DTOOfferRule,
  ): Promise<OfferRule> {
    return fetchApi(courseProductRelationsRoutes.addOfferRule(relationId), {
      method: "POST",
      body: exportToFormData(offerRule),
    }).then(checkStatus);
  }

  static editOfferRule(
    relationId: string,
    offerRuleId: string,
    offerRule: DTOOfferRule,
  ): Promise<OfferRule> {
    return fetchApi(
      courseProductRelationsRoutes.editOfferRule(relationId, offerRuleId),
      {
        method: "PATCH",
        body: exportToFormData(offerRule),
      },
    ).then(checkStatus);
  }
  static deleteOfferRule(
    relationId: string,
    offerRuleId: string,
  ): Promise<OfferRule> {
    return fetchApi(
      courseProductRelationsRoutes.deleteOfferRule(relationId, offerRuleId),
      {
        method: "DELETE",
      },
    ).then(checkStatus);
  }

  static checkStatutCertificateGenerationProcess(id: string): Promise<any> {
    return fetchApi(
      courseProductRelationsRoutes.checkCertificateGeneration(id),
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept-Language": getAcceptLanguage(),
        },
      },
    ).then(checkStatus);
  }

  static generateMultipleCertificate(id: string): Promise<any> {
    return fetchApi(
      courseProductRelationsRoutes.generateMultipleCertificate(id),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept-Language": getAcceptLanguage(),
        },
      },
    ).then(checkStatus);
  }
};
