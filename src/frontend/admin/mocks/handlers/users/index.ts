import { rest } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { userRoutes } from "@/services/repositories/Users/UsersRepository";
import { UsersFactory } from "@/services/factories/users";

export const userHandlers = [
  rest.get(buildApiUrl(userRoutes.getAll()), (req, res, ctx) => {
    return res(ctx.json(UsersFactory(10)));
  }),
  rest.get(buildApiUrl(userRoutes.get(":id")), (req, res, ctx) => {
    return res(ctx.json(UsersFactory()));
  }),
];
