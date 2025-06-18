import queryString from "query-string";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import {
  checkStatus,
  fetchApi,
  getAcceptLanguage,
} from "@/services/http/HttpService";
import { Offer, DTOOffer } from "@/services/api/models/Offers";
import { DTOOfferRule, OfferRule } from "@/services/api/models/OfferRule";
import { exportToFormData } from "@/utils/forms";
import { PaginatedResponse } from "@/types/api";

export const offersRoutes = {
  getAll: (params: string = "") => `/offers/${params}`,
  create: `/offers/`,
  get: (id: string, params: string = "") => `/offers/${id}/${params}`,
  update: (id: string) => `/offers/${id}/`,
  delete: (id: string) => `/offers/${id}/`,
  addOfferRule: (id: string) => `/offers/${id}/offer-rules/`,
  editOfferRule: (id: string, offerRuleId: string) =>
    `/offers/${id}/offer-rules/${offerRuleId}/`,
  deleteOfferRule: (id: string, offerRuleId: string) =>
    `/offers/${id}/offer-rules/${offerRuleId}/`,
  checkCertificateGeneration: (id: string) =>
    `/offers/${id}/check_certificates_generation_process/`,

  generateMultipleCertificate: (id: string) =>
    `/offers/${id}/generate_certificates/`,
};

export const OfferRepository = class OfferRepository {
  static get(id: string, filters?: Maybe<ResourcesQuery>): Promise<Offer> {
    const url = offersRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<PaginatedResponse<Offer>> {
    const url = offersRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static create(payload: DTOOffer): Promise<Offer> {
    return fetchApi(offersRoutes.create, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(offersRoutes.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(id: string, payload: DTOOffer): Promise<Offer> {
    return fetchApi(offersRoutes.update(id), {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }

  static addOfferRule(
    offerId: string,
    offerRule: DTOOfferRule,
  ): Promise<OfferRule> {
    return fetchApi(offersRoutes.addOfferRule(offerId), {
      method: "POST",
      body: exportToFormData(offerRule),
    }).then(checkStatus);
  }

  static editOfferRule(
    offerId: string,
    offerRuleId: string,
    offerRule: DTOOfferRule,
  ): Promise<OfferRule> {
    return fetchApi(offersRoutes.editOfferRule(offerId, offerRuleId), {
      method: "PATCH",
      body: exportToFormData(offerRule),
    }).then(checkStatus);
  }
  static deleteOfferRule(
    offerId: string,
    offerRuleId: string,
  ): Promise<OfferRule> {
    return fetchApi(offersRoutes.deleteOfferRule(offerId, offerRuleId), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static checkStatutCertificateGenerationProcess(id: string): Promise<any> {
    return fetchApi(offersRoutes.checkCertificateGeneration(id), {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }

  static generateMultipleCertificate(id: string): Promise<any> {
    return fetchApi(offersRoutes.generateMultipleCertificate(id), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }
};
