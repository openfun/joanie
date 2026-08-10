import { render, screen } from "@testing-library/react";
import * as React from "react";
import { OrderView } from "@/components/templates/orders/view/OrderView";
import { OrderFactory } from "@/services/factories/orders";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { formatShortDate } from "@/utils/dates";

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

describe("<OrderView /> withdrawal dates", () => {
  it("does not render the withdrawal fields when the order has no withdrawal request", () => {
    const order = OrderFactory();
    order.withdrawn_requested_at = null;
    order.withdrawn_confirmation_at = null;

    render(<OrderView order={order} />, { wrapper: TestingWrapper });

    expect(
      screen.queryByLabelText("Withdrawal requested on"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Withdrawal confirmed on"),
    ).not.toBeInTheDocument();
  });

  it("renders the withdrawal requested date when present", () => {
    const order = OrderFactory();
    order.withdrawn_requested_at = "2024-06-27T10:00:00Z";
    order.withdrawn_confirmation_at = null;

    render(<OrderView order={order} />, { wrapper: TestingWrapper });

    expect(screen.getByLabelText("Withdrawal requested on")).toHaveValue(
      formatShortDate(order.withdrawn_requested_at),
    );
  });

  it("renders the withdrawal confirmation date when present", () => {
    const order = OrderFactory();
    order.withdrawn_requested_at = "2024-06-27T10:00:00Z";
    order.withdrawn_confirmation_at = "2024-06-28T10:00:00Z";

    render(<OrderView order={order} />, { wrapper: TestingWrapper });

    expect(screen.getByLabelText("Withdrawal confirmed on")).toHaveValue(
      formatShortDate(order.withdrawn_confirmation_at),
    );
  });
});
