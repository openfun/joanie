import { rest } from "msw";

import { OrganizationFactory } from "@/services/factories/organizations";
import { buildApiUrl } from "@/services/http/HttpService";
import { organizationRoute } from "@/services/repositories/organization/OrganizationRepository";

export const organizationHandlers = [
  rest.get(buildApiUrl(organizationRoute.getAll()), (req, res, ctx) => {
    return res(ctx.json(OrganizationFactory(10)));
  }),
  rest.get(buildApiUrl(organizationRoute.get(":id")), (req, res, ctx) => {
    return res(ctx.json(OrganizationFactory()));
  }),
];
