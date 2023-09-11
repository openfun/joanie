import { organizationHandlers } from "./organizations";
import { certificateDefinitionsHandlers } from "./certificate-definitions";
import { coursesRunsHandlers } from "./courses-runs";
import { coursesHandlers } from "./courses";
import { authHandlers } from "./auth";
import { userHandlers } from "./users";
import { productHandlers } from "./products";

export const handlers = [
  ...organizationHandlers,
  ...certificateDefinitionsHandlers,
  ...coursesRunsHandlers,
  ...coursesHandlers,
  ...userHandlers,
  ...authHandlers,
  ...productHandlers,
];
