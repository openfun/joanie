import { rest } from "msw";
import { organizationHandlers } from "./organizations";
import { certificateDefinitionsHandlers } from "./certificate-definitions";
import { coursesRunsHandlers } from "./courses-runs";
import { coursesHandlers } from "./courses";
import { buildApiUrl } from "@/services/http/HttpService";

export const handlers = [
  ...organizationHandlers,
  ...certificateDefinitionsHandlers,
  ...coursesRunsHandlers,
  ...coursesHandlers,
  rest.get(buildApiUrl("/toto"), (req, res, ctx) => {
    return res(ctx.json({ firstName: "John" }));
  }),
];
