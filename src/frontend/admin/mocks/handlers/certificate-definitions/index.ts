import { http, HttpResponse } from "msw";

import { CertificateDefinitionFactory } from "@/services/factories/certificate-definition";
import { buildApiUrl } from "@/services/http/HttpService";
import { certificateDefinitionRoutes } from "@/services/repositories/certificate-definition/CertificateDefinitionRepository";

export const certificateDefinitionsHandlers = [
  http.get(buildApiUrl(certificateDefinitionRoutes.getAll()), () => {
    return HttpResponse.json(CertificateDefinitionFactory(10));
  }),
  http.get(buildApiUrl(certificateDefinitionRoutes.get(":id")), () => {
    return HttpResponse.json(CertificateDefinitionFactory());
  }),
];
