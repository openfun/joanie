import { organizationHandlers } from "./organizations";
import { certificateDefinitionsHandlers } from "./certificate-definitions";
import { coursesRunsHandlers } from "./courses-runs";
import { coursesHandlers } from "./courses";
import { authHandlers } from "./auth";

export const handlers = [
  ...organizationHandlers,
  ...certificateDefinitionsHandlers,
  ...coursesRunsHandlers,
  ...coursesHandlers,
  ...authHandlers,
];
