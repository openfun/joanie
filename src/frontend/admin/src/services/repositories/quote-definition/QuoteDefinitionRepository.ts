import queryString from "query-string";
import { BaseEntityRoutesPaths } from "@/types/routes";
import { AbstractRepository } from "@/services/repositories/AbstractRepository";

import { Maybe } from "@/types/utils";
import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { exportToFormData } from "@/utils/forms";
import {
  QuoteDefinition,
  DTOQuoteDefinition,
} from "@/services/api/models/QuoteDefinition";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { PaginatedResponse } from "@/types/api";
import { SelectOption } from "@/components/presentational/hook-form/RHFSelect";

export const quoteDefinitionRoutes: BaseEntityRoutesPaths = {
  get: (id: string, params: string = "") =>
    `/quote-definitions/${id}/${params}`,
  getAll: (params: string = "") => `/quote-definitions/${params}`,
  create: "/quote-definitions/",
  update: (id: string) => `/quote-definitions/${id}/`,
  delete: (id: string) => `/quote-definitions/${id}/`,
};

interface Repository extends AbstractRepository<
  QuoteDefinition,
  ResourcesQuery,
  DTOQuoteDefinition
> {
  getAllLanguages: () => Promise<SelectOption[]>;
  getAllTemplates: () => Promise<SelectOption[]>;
}

export const QuoteDefinitionRepository: Repository = class QuoteDefinitionRepository {
  static get(
    id: string,
    filters?: Maybe<ResourcesQuery>,
  ): Promise<QuoteDefinition> {
    const url = quoteDefinitionRoutes.get(
      id,
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static getAll(
    filters: Maybe<ResourcesQuery>,
  ): Promise<PaginatedResponse<QuoteDefinition>> {
    const url = quoteDefinitionRoutes.getAll(
      filters ? `?${queryString.stringify(filters)}` : "",
    );
    return fetchApi(url, { method: "GET" }).then(checkStatus);
  }

  static create(payload: DTOQuoteDefinition): Promise<QuoteDefinition> {
    return fetchApi(quoteDefinitionRoutes.create, {
      method: "POST",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static delete(id: string): Promise<void> {
    return fetchApi(quoteDefinitionRoutes.delete(id), {
      method: "DELETE",
    }).then(checkStatus);
  }

  static update(
    id: string,
    payload: DTOQuoteDefinition,
  ): Promise<QuoteDefinition> {
    return fetchApi(quoteDefinitionRoutes.update(id), {
      method: "PATCH",
      body: exportToFormData(payload),
    }).then(checkStatus);
  }

  static getAllLanguages(): Promise<SelectOption[]> {
    return fetchApi(quoteDefinitionRoutes.getAll(), {
      method: "OPTIONS",
    }).then(async (response) => {
      const checkedResponse = await checkStatus(response);
      const result: { value: string; display_name: string }[] =
        checkedResponse.actions.POST.language.choices;
      return result.map(({ value, display_name: label }) => ({
        value,
        label,
      }));
    });
  }

  static getAllTemplates(): Promise<SelectOption[]> {
    return fetchApi(quoteDefinitionRoutes.getAll(), {
      method: "OPTIONS",
    }).then(async (response) => {
      const checkedResponse = await checkStatus(response);
      const result: { value: string; display_name: string }[] =
        checkedResponse.actions.POST.name.choices;
      return result.map(({ value, display_name: label }) => ({
        value,
        label,
      }));
    });
  }
};
