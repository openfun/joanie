import queryString from "query-string";
import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import {
  checkStatus,
  fetchApi,
  getAcceptLanguage,
} from "@/services/http/HttpService";
import { OfferingRule } from "@/services/api/models/OfferingRule";

export const offeringRulesRoutes = {
  get: (id: string, offeringId: string, params: string = "") =>
    `/offerings/${offeringId}/offering-rules/${id}/${params}`,
};

export const OfferingRuleRepository = class OfferingRuleRepository {
  static get(
    id: string,
    offeringId: string,
    filters?: Maybe<ResourcesQuery>,
  ): Promise<OfferingRule> {
    const url = offeringRulesRoutes.get(
      id,
      offeringId,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getAcceptLanguage(),
      },
    }).then(checkStatus);
  }
};
