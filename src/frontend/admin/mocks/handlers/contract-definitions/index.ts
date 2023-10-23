import { rest } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { contractDefinitionRoutes } from "@/services/repositories/contract-definition/ContractDefinitionRepository";
import { ContractDefinitionFactory } from "@/services/factories/contract-definition";

export const contractDefinitionsHandlers = [
  rest.get(buildApiUrl(contractDefinitionRoutes.getAll()), (req, res, ctx) => {
    return res(ctx.json(ContractDefinitionFactory(10)));
  }),
  rest.get(
    buildApiUrl(contractDefinitionRoutes.get(":id")),
    (req, res, ctx) => {
      return res(ctx.json(ContractDefinitionFactory()));
    },
  ),
];
