import queryString from "query-string";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import {
  checkStatus,
  fetchApi,
  getAcceptLanguage,
} from "@/services/http/HttpService";
import { Offering, DTOOffering } from "@/services/api/models/Offerings";
import {
  DTOOfferingRule,
  OfferingRule,
} from "@/services/api/models/OfferingRule";
import { exportToFormData } from "@/utils/forms";
import { PaginatedResponse } from "@/types/api";

export const offeringsRoutes = {
  getAll: (params: string = "") => `/offerings/${params}`,
  create: `/offerings/`,
  get: (id: string, params: string = "") => `/offerings/${id}/${params}`,
  update: (id: string) => `/offerings/${id}/`,
  delete: (id: string) => `/offerings/${id}/`,
  getOfferingRule: (id: string, offeringRuleId: string) =>
    `/offerings/${id}/offering-rules/${offeringRuleId}/`,
  addOfferingRule: (id: string) => `/offerings/${id}/offering-rules/`,
  editOfferingRule: (id: string, offeringRuleId: string) =>
    `/offerings/${id}/offering-rules/${offeringRuleId}/`,
  deleteOfferingRule: (id: string, offeringRuleId: string) =>
    `/offerings/${id}/offering-rules/${offeringRuleId}/`,
  checkCertificateGeneration: (id: string) =>
    `/offerings/${id}/check_certificates_generation_process/`,

  generateMultipleCertificate: (id: string) =>
    `/offerings/${id}/generate_certificates/`,
};

export const OfferingRepository = class OfferingRepository {
  static get(id: string, filters?: Maybe<ResourcesQuery>): Promise<Offering> {
    const url = offeringsRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<PaginatedResponse<Offering>> {
    const url = offeringsRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static create(payload: DTOOffering): Promise<Offering> {
    return fetchApi(offeringsRoutes.create, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(offeringsRoutes.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(id: string, payload: DTOOffering): Promise<Offering> {
    return fetchApi(offeringsRoutes.update(id), {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }

  static getOfferingRule(
    offeringId: string,
    offeringRuleId: string,
  ): Promise<OfferingRule> {
    const url = offeringsRoutes.getOfferingRule(
      offeringId, offeringRuleId
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static addOfferingRule(
    offeringId: string,
    offeringRule: DTOOfferingRule,
  ): Promise<OfferingRule> {
    return fetchApi(offeringsRoutes.addOfferingRule(offeringId), {
      method: "POST",
      body: exportToFormData(offeringRule),
    }).then(checkStatus);
  }

  static editOfferingRule(
    offeringId: string,
    offeringRuleId: string,
    offeringRule: DTOOfferingRule,
  ): Promise<OfferingRule> {
    return fetchApi(
      offeringsRoutes.editOfferingRule(offeringId, offeringRuleId),
      {
        method: "PATCH",
        body: exportToFormData(offeringRule),
      },
    ).then(checkStatus);
  }
  static deleteOfferingRule(
    offeringId: string,
    offeringRuleId: string,
  ): Promise<OfferingRule> {
    return fetchApi(
      offeringsRoutes.deleteOfferingRule(offeringId, offeringRuleId),
      {
        method: "DELETE",
      },
    ).then(checkStatus);
  }

  static checkStatutCertificateGenerationProcess(id: string): Promise<any> {
    return fetchApi(offeringsRoutes.checkCertificateGeneration(id), {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }

  static generateMultipleCertificate(id: string): Promise<any> {
    return fetchApi(offeringsRoutes.generateMultipleCertificate(id), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }
};
