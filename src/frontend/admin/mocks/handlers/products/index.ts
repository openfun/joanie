import { rest } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { productRoute } from "@/services/repositories/products/ProductRepository";
import { ProductFactory } from "@/services/factories/product";

export const productHandlers = [
  rest.get(buildApiUrl(productRoute.getAll()), (req, res, ctx) => {
    return res(ctx.json(ProductFactory(10)));
  }),
  rest.get(buildApiUrl(productRoute.get(":id")), (req, res, ctx) => {
    return res(ctx.json(ProductFactory()));
  }),
  rest.post(buildApiUrl(productRoute.create), async (req, res, ctx) => {
    // return res(ctx.json(req.json()));
    return res(ctx.json(ProductFactory()));
  }),
  rest.post(buildApiUrl(productRoute.update(":id")), async (req, res, ctx) => {
    return res(ctx.json(ProductFactory()));
  }),
  rest.patch(buildApiUrl(productRoute.update(":id")), async (req, res, ctx) => {
    // return res(ctx.json(ProductFactory()));
    const a = await req.json();
    return res(ctx.json(ProductFactory()));
    // return res(ctx.json({}));
  }),
];
