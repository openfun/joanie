import { rest } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { authApiRoutes } from "@/services/repositories/auth/AuthRepository";

export const authHandlers = [
  rest.get(buildApiUrl(authApiRoutes.me), (req, res, ctx) => {
    return res(
      ctx.json({
        abilities: {
          delete: false,
          get: true,
          has_course_access: true,
          has_organization_access: true,
          patch: true,
          put: true,
        },
        full_name: "",
        id: "ad2be34d-ab38-407f-a5d1-33eadb592023",
        is_staff: true,
        is_superuser: true,
        username: "admin",
      }),
    );
  }),
];
