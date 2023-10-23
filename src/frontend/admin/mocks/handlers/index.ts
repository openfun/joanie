import { organizationHandlers } from "./organizations";
import { certificateDefinitionsHandlers } from "./certificate-definitions";
import { coursesRunsHandlers } from "./courses-runs";
import { coursesHandlers } from "./courses";
import { authHandlers } from "./auth";
import { userHandlers } from "./users";
import { productHandlers } from "./products";
import { contractDefinitionsHandlers } from "./contract-definitions";

export const handlers = [
  ...organizationHandlers,
  ...certificateDefinitionsHandlers,
  ...contractDefinitionsHandlers,
  ...coursesRunsHandlers,
  ...coursesHandlers,
  ...userHandlers,
  ...authHandlers,
  ...productHandlers,
];
