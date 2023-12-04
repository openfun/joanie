import { http, HttpResponse } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { contractDefinitionRoutes } from "@/services/repositories/contract-definition/ContractDefinitionRepository";
import { ContractDefinitionFactory } from "@/services/factories/contract-definition";

export const contractDefinitionsHandlers = [
  http.get(buildApiUrl(contractDefinitionRoutes.getAll()), () => {
    return HttpResponse.json(ContractDefinitionFactory(10));
  }),
  http.get(buildApiUrl(contractDefinitionRoutes.get(":id")), () => {
    return HttpResponse.json(ContractDefinitionFactory());
  }),
];
