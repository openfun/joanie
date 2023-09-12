import { render, screen, waitFor } from "@testing-library/react";
import { rest } from "msw";
import { server } from "../../../../../mocks/server";
import { ProductList } from "@/components/templates/products/list/ProductsList";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { buildApiUrl } from "@/services/http/HttpService";
import { productRoute } from "@/services/repositories/products/ProductRepository";
import { ProductFactory } from "@/services/factories/product";

describe("<ProductList />", () => {
  const allProducts = ProductFactory(4);
  beforeEach(() => {
    server.use(
      rest.get(buildApiUrl(productRoute.getAll()), (req, res, ctx) => {
        return res(ctx.json(allProducts));
      }),
    );
  });

  it("renders ProductList component and test if everything is displayed well", async () => {
    render(<ProductList />, { wrapper: TestingWrapper });
    await screen.findByText("Title");
    screen.getByText("type");
    screen.getByText("price");
    await waitFor(() => {
      allProducts.forEach((product) => {
        screen.getByText(product.title);
        if (product.price) {
          screen.getByText(product.price);
        }
      });
    });
  });
});
