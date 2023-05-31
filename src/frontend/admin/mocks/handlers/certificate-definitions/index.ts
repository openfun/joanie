import { rest } from "msw";

import { CertificateDefinitionFactory } from "@/services/factories/certificate-definition";
import { buildApiUrl } from "@/services/http/HttpService";
import { certificateDefinitionRoutes } from "@/services/repositories/certificate-definition/CertificateDefinitionRepository";

export const certificateDefinitionsHandlers = [
  rest.get(
    buildApiUrl(certificateDefinitionRoutes.getAll()),
    (req, res, ctx) => {
      return res(ctx.json(CertificateDefinitionFactory(10)));
    }
  ),
  rest.get(
    buildApiUrl(certificateDefinitionRoutes.get(":id")),
    (req, res, ctx) => {
      return res(ctx.json(CertificateDefinitionFactory()));
    }
  ),
];
