import { http, HttpResponse } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { userRoutes } from "@/services/repositories/Users/UsersRepository";
import { UsersFactory } from "@/services/factories/users";

export const userHandlers = [
  http.get(buildApiUrl(userRoutes.getAll()), () => {
    return HttpResponse.json(UsersFactory(10));
  }),
  http.get(buildApiUrl(userRoutes.get(":id")), () => {
    return HttpResponse.json(UsersFactory());
  }),
];
