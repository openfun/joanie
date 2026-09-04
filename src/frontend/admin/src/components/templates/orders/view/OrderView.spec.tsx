import { render, screen } from "@testing-library/react";
import * as React from "react";
import { OrderView } from "@/components/templates/orders/view/OrderView";
import { OrderFactory } from "@/services/factories/orders";
import { OrderStatesEnum } from "@/services/api/models/Order";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

jest.mock("@/hooks/useCopyToClipboard", () => ({
  useCopyToClipboard: () => jest.fn(),
}));

describe("<OrderView /> voucher section", () => {
  it("does not render the voucher field when order has no voucher", () => {
    const order = OrderFactory();
    order.voucher = null;

    render(<OrderView order={order} />, { wrapper: TestingWrapper });

    expect(screen.queryByLabelText("Voucher code")).not.toBeInTheDocument();
  });

  it("renders the voucher code with a copy button when the voucher is available", () => {
    const order = OrderFactory();
    order.voucher = { code: "AVAILABLE-CODE", is_used: false };

    render(<OrderView order={order} />, { wrapper: TestingWrapper });

    expect(screen.getByLabelText("Voucher code")).toBeInTheDocument();
    expect(screen.getByDisplayValue("AVAILABLE-CODE")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Click to copy" }),
    ).toBeInTheDocument();
  });

  it("renders the voucher code without a copy button when the voucher has been used", () => {
    const order = OrderFactory();
    order.voucher = { code: "USED-CODE", is_used: true };

    render(<OrderView order={order} />, { wrapper: TestingWrapper });

    expect(screen.getByLabelText("Voucher code")).toBeInTheDocument();
    expect(screen.getByDisplayValue("USED-CODE")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Click to copy" }),
    ).not.toBeInTheDocument();
  });
});

describe("<OrderView /> state field", () => {
  it("renders the pending_withdraw state without crashing", () => {
    const order = OrderFactory();
    order.state = OrderStatesEnum.ORDER_STATE_PENDING_WITHDRAW;

    render(<OrderView order={order} />, { wrapper: TestingWrapper });

    expect(screen.getByDisplayValue("To withdraw")).toBeInTheDocument();
  });
});
