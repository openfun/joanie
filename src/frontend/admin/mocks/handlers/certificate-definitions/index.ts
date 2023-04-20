import { rest } from "msw";

import { createDummyCertificatesDefinitions } from "@/services/factories/certificate-definition/certificationDefinitionFactory";
import { buildApiUrl } from "@/services/http/HttpService";
import { certificateDefinitionRoutes } from "@/services/repositories/certificate-definition/CertificateDefinitionRepository";

export const certificateDefinitionsHandlers = [
  rest.get(
    buildApiUrl(certificateDefinitionRoutes.getAll()),
    (req, res, ctx) => {
      const productId = req.url.searchParams.get("search");
      console.log(productId);
      return res(ctx.json(createDummyCertificatesDefinitions()));
    }
  ),
];
