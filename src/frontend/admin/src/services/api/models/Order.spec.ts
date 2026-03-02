import { transformOrderToOrderListItem } from "@/services/api/models/Order";
import { OrderFactory } from "@/services/factories/orders";

describe("transformOrderToOrderListItem", () => {
  it("maps voucher code when the order has a voucher", () => {
    const order = OrderFactory();
    order.voucher = { code: "MY-VOUCHER", is_used: false };

    const item = transformOrderToOrderListItem(order);

    expect(item.voucher).toBe("MY-VOUCHER");
  });

  it("maps voucher to null when the order has no voucher", () => {
    const order = OrderFactory();
    order.voucher = null;

    const item = transformOrderToOrderListItem(order);

    expect(item.voucher).toBeNull();
  });
});
