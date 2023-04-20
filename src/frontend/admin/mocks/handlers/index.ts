import { organizationHandlers } from "./organizations";
import { certificateDefinitionsHandlers } from "./certificate-definitions";
import { coursesRunsHandlers } from "./courses-runs";
import { coursesHandlers } from "./courses";

export const handlers = [
  ...organizationHandlers,
  ...certificateDefinitionsHandlers,
  ...coursesRunsHandlers,
  ...coursesHandlers,
];
