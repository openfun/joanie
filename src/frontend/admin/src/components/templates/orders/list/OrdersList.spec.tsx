import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import * as React from "react";
import { server } from "mocks/server";
import { OrderListItemFactory } from "@/services/factories/orders";
import { buildApiUrl } from "@/services/http/HttpService";
import { orderRoutes } from "@/services/repositories/orders/OrderRepository";
import { OrdersList } from "@/components/templates/orders/list/OrdersList";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

jest.mock("@/hooks/useCopyToClipboard", () => ({
  useCopyToClipboard: () => jest.fn(),
}));

describe("<OrdersList /> voucher column", () => {
  const orderWithVoucher = OrderListItemFactory();
  orderWithVoucher.voucher = "VOUCHER-CODE-123";

  const orderWithoutVoucher = OrderListItemFactory();
  orderWithoutVoucher.voucher = null;

  beforeEach(() => {
    server.use(
      http.get(buildApiUrl(orderRoutes.getAll()), () => {
        return HttpResponse.json({
          count: 2,
          results: [orderWithVoucher, orderWithoutVoucher],
          next: null,
          previous: null,
        });
      }),
    );
  });

  it("renders the voucher code with a copy button when voucher is present", async () => {
    render(<OrdersList />, { wrapper: TestingWrapper });
    await screen.findByText("VOUCHER-CODE-123");
    screen.getByRole("button", { name: /copy/i });
  });

  it("renders nothing in the voucher cell when voucher is absent", async () => {
    render(<OrdersList />, { wrapper: TestingWrapper });
    await screen.findByText("VOUCHER-CODE-123");
    // Only one copy button — the row without voucher renders nothing
    expect(screen.getAllByRole("button", { name: /copy/i })).toHaveLength(1);
  });

  it("calls copyToClipboard with the voucher code on button click", async () => {
    const copyToClipboard = jest.fn();
    jest
      .spyOn(require("@/hooks/useCopyToClipboard"), "useCopyToClipboard")
      .mockReturnValue(copyToClipboard);

    render(<OrdersList />, { wrapper: TestingWrapper });
    const button = await screen.findByRole("button", { name: /copy/i });
    await userEvent.click(button);
    expect(copyToClipboard).toHaveBeenCalledWith("VOUCHER-CODE-123");
  });
});
