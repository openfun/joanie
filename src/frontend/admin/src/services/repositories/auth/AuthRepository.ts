import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { exportToFormData } from "@/utils/forms";

export class AuthRepository {
  static login(username: string, password: string): Promise<any> {
    return fetchApi("/auth/login", {
      method: "POST",
      body: exportToFormData({ username, password }),
    }).then(checkStatus);
  }

  static logout(): Promise<any> {
    return fetchApi("/auth/logout", {
      method: "POST",
    }).then(checkStatus);
  }

  static forgotPassword(email: string): Promise<any> {
    return fetchApi("/auth/forgot-password", {
      method: "POST",
      body: exportToFormData({ email }),
    }).then(checkStatus);
  }
}
