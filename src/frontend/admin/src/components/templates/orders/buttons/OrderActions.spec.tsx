import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import * as React from "react";
import { server } from "mocks/server";
import OrderActionsButton from "@/components/templates/orders/buttons/OrderActions";
import { OrderFactory } from "@/services/factories/orders";
import { buildApiUrl } from "@/services/http/HttpService";
import { orderRoutes } from "@/services/repositories/orders/OrderRepository";
import { OrderStatesEnum } from "@/services/api/models/Order";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

const openActionsMenu = async () => {
  const button = screen.getByRole("button", { name: /actions/i });
  await userEvent.click(button);
};

describe("<OrderActionsButton /> withdrawal actions", () => {
  it("disables confirm and reject withdrawal actions when the order has no pending withdrawal request", async () => {
    const order = OrderFactory();
    order.state = OrderStatesEnum.ORDER_STATE_COMPLETED;
    server.use(
      http.get(buildApiUrl(orderRoutes.get(order.id)), () =>
        HttpResponse.json(order),
      ),
    );

    render(<OrderActionsButton order={order} />, { wrapper: TestingWrapper });
    await openActionsMenu();

    expect(
      screen.getByRole("menuitem", { name: "Confirm withdrawal" }),
    ).toHaveAttribute("aria-disabled", "true");
    expect(
      screen.getByRole("menuitem", { name: "Reject withdrawal" }),
    ).toHaveAttribute("aria-disabled", "true");
  });

  it("enables confirm and reject withdrawal actions when the order has a pending withdrawal request", async () => {
    const order = OrderFactory();
    order.state = OrderStatesEnum.ORDER_STATE_PENDING_WITHDRAW;
    server.use(
      http.get(buildApiUrl(orderRoutes.get(order.id)), () =>
        HttpResponse.json(order),
      ),
    );

    render(<OrderActionsButton order={order} />, { wrapper: TestingWrapper });
    await openActionsMenu();

    expect(
      screen.getByRole("menuitem", { name: "Confirm withdrawal" }),
    ).not.toHaveAttribute("aria-disabled", "true");
    expect(
      screen.getByRole("menuitem", { name: "Reject withdrawal" }),
    ).not.toHaveAttribute("aria-disabled", "true");
  });

  it("sends a confirm-withdrawal request when clicking Confirm withdrawal", async () => {
    const order = OrderFactory();
    order.state = OrderStatesEnum.ORDER_STATE_PENDING_WITHDRAW;
    const onConfirmWithdrawal = jest.fn();
    server.use(
      http.get(buildApiUrl(orderRoutes.get(order.id)), () =>
        HttpResponse.json(order),
      ),
      http.post(buildApiUrl(orderRoutes.confirmWithdrawal(order.id)), () => {
        onConfirmWithdrawal();
        return HttpResponse.json(null);
      }),
    );

    render(<OrderActionsButton order={order} />, { wrapper: TestingWrapper });
    await openActionsMenu();
    await userEvent.click(
      screen.getByRole("menuitem", { name: "Confirm withdrawal" }),
    );

    expect(onConfirmWithdrawal).toHaveBeenCalledTimes(1);
  });

  it("sends a reject-withdrawal request when clicking Reject withdrawal", async () => {
    const order = OrderFactory();
    order.state = OrderStatesEnum.ORDER_STATE_PENDING_WITHDRAW;
    const onRejectWithdrawal = jest.fn();
    server.use(
      http.get(buildApiUrl(orderRoutes.get(order.id)), () =>
        HttpResponse.json(order),
      ),
      http.post(buildApiUrl(orderRoutes.rejectWithdrawal(order.id)), () => {
        onRejectWithdrawal();
        return HttpResponse.json(null);
      }),
    );

    render(<OrderActionsButton order={order} />, { wrapper: TestingWrapper });
    await openActionsMenu();
    await userEvent.click(
      screen.getByRole("menuitem", { name: "Reject withdrawal" }),
    );

    expect(onRejectWithdrawal).toHaveBeenCalledTimes(1);
  });
});
