import { render, screen } from "@testing-library/react";
import * as React from "react";
import { OrderView } from "@/components/templates/orders/view/OrderView";
import { OrderFactory } from "@/services/factories/orders";
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

  it("renders the voucher code when the voucher is available", () => {
    const order = OrderFactory();
    order.voucher = { code: "AVAILABLE-CODE", is_used: false };

    render(<OrderView order={order} />, { wrapper: TestingWrapper });

    expect(screen.getByLabelText("Voucher code")).toBeInTheDocument();
    expect(screen.getByDisplayValue("AVAILABLE-CODE")).toBeInTheDocument();
  });

  it("renders the voucher code when the voucher has been used", () => {
    const order = OrderFactory();
    order.voucher = { code: "USED-CODE", is_used: true };

    render(<OrderView order={order} />, { wrapper: TestingWrapper });

    expect(screen.getByLabelText("Voucher code")).toBeInTheDocument();
    expect(screen.getByDisplayValue("USED-CODE")).toBeInTheDocument();
  });
});
