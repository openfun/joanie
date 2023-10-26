import { rest } from "msw";

import { OrganizationFactory } from "@/services/factories/organizations";
import { buildApiUrl } from "@/services/http/HttpService";
import { organizationRoute } from "@/services/repositories/organization/OrganizationRepository";

export const organizationHandlers = [
  rest.get(buildApiUrl(organizationRoute.getAll()), (req, res, ctx) => {
    const result = {
      count: 10,
      next: null,
      previous: null,
      results: OrganizationFactory(10),
    };
    return res(ctx.json(result));
  }),
  rest.get(buildApiUrl(organizationRoute.get(":id")), (req, res, ctx) => {
    return res(ctx.json(OrganizationFactory()));
  }),
  rest.post(
    buildApiUrl(organizationRoute.addUserAccess(":id")),
    (req, res, ctx) => {
      return res(ctx.json(OrganizationFactory()));
    },
  ),
  rest.options(buildApiUrl(organizationRoute.options), (req, res, ctx) => {
    const result = {
      actions: {
        POST: {
          accesses: {
            child: {
              children: {
                role: {
                  choices: [
                    {
                      value: "owner",
                      display_name: "owner",
                    },
                    {
                      value: "administrator",
                      display_name: "administrator",
                    },
                    {
                      value: "member",
                      display_name: "member",
                    },
                  ],
                },
              },
            },
          },
        },
      },
    };
    return res(ctx.json(result));
  }),
];
