import {
  getOrderStateMessage,
  orderStatesMessages,
  orderStateWithdrawnMessage,
} from "@/components/templates/orders/view/translations";
import { OrderStatesEnum } from "@/services/api/models/Order";

describe("getOrderStateMessage", () => {
  it("returns the withdrawn message for a canceled order with a withdrawal confirmation date", () => {
    const message = getOrderStateMessage({
      state: OrderStatesEnum.ORDER_STATE_CANCELED,
      withdrawn_confirmation_at: "2024-06-27T10:00:00Z",
    });

    expect(message).toBe(orderStateWithdrawnMessage);
  });

  it("returns the canceled message for a canceled order without a withdrawal confirmation date", () => {
    const message = getOrderStateMessage({
      state: OrderStatesEnum.ORDER_STATE_CANCELED,
      withdrawn_confirmation_at: null,
    });

    expect(message).toBe(orderStatesMessages.canceled);
  });

  it("returns the regular state message for a non-canceled state", () => {
    const message = getOrderStateMessage({
      state: OrderStatesEnum.ORDER_STATE_PENDING_WITHDRAW,
      withdrawn_confirmation_at: null,
    });

    expect(message).toBe(orderStatesMessages.pending_withdraw);
  });
});
