import { http, HttpResponse } from "msw";

import { OrganizationFactory } from "@/services/factories/organizations";
import { buildApiUrl } from "@/services/http/HttpService";
import { organizationRoute } from "@/services/repositories/organization/OrganizationRepository";

export const organizationHandlers = [
  http.get(buildApiUrl(organizationRoute.getAll()), () => {
    const result = {
      count: 10,
      next: null,
      previous: null,
      results: OrganizationFactory(10),
    };
    return HttpResponse.json(result);
  }),
  http.get(buildApiUrl(organizationRoute.get(":id")), () => {
    return HttpResponse.json(OrganizationFactory());
  }),
  http.post(buildApiUrl(organizationRoute.addUserAccess(":id")), () => {
    return HttpResponse.json(OrganizationFactory());
  }),
  http.options(buildApiUrl(organizationRoute.options), () => {
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

    return HttpResponse.json(result);
  }),
];
