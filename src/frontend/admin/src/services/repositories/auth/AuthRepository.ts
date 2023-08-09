import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { AuthenticatedUser } from "@/types/auth";

export const authApiRoutes = {
  me: `/users/me/`,
};

export class AuthRepository {
  static async me(): Promise<AuthenticatedUser> {
    return fetchApi(authApiRoutes.me, { method: "GET" }).then(checkStatus);
  }
}
