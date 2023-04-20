import { rest } from "msw";

import {
  createDummyOrganization,
  createDummyOrganizations,
} from "@/services/factories/organizations/organizationFactory";
import { buildApiUrl } from "@/services/http/HttpService";
import { organizationRoute } from "@/services/repositories/organization/OrganizationRepository";

export const organizationHandlers = [
  rest.get(buildApiUrl(organizationRoute.getAll()), (req, res, ctx) => {
    return res(ctx.json(createDummyOrganizations(100)));
  }),
  rest.get(buildApiUrl(organizationRoute.get(":id")), (req, res, ctx) => {
    return res(ctx.json(createDummyOrganization()));
  }),
];
