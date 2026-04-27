import { checkStatus, fetchApi } from "@/services/http/HttpService";
import { WaffleStatus } from "@/services/api/models/Waffle";

export const waffleRoutes = {
  getStatus: "/waffle_status/",
};

export const WaffleRepository = class WaffleRepository {
  static getStatus(): Promise<WaffleStatus> {
    return fetchApi(waffleRoutes.getStatus, { method: "GET" }).then(
      checkStatus,
    );
  }
};
