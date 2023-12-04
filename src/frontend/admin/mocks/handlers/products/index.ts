import { http, HttpResponse } from "msw";
import { buildApiUrl } from "@/services/http/HttpService";
import { productRoute } from "@/services/repositories/products/ProductRepository";
import { ProductFactory } from "@/services/factories/product";

export const productHandlers = [
  http.get(buildApiUrl(productRoute.getAll()), () => {
    return HttpResponse.json(ProductFactory(10));
  }),
  http.get(buildApiUrl(productRoute.get(":id")), () => {
    return HttpResponse.json(ProductFactory());
  }),
  http.post(buildApiUrl(productRoute.create), async () => {
    return HttpResponse.json(ProductFactory());
  }),
  http.post(buildApiUrl(productRoute.update(":id")), async () => {
    return HttpResponse.json(ProductFactory());
  }),
  http.patch(buildApiUrl(productRoute.update(":id")), async () => {
    return HttpResponse.json(ProductFactory());
  }),
];
