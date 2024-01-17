import { OrderListItemFactory } from "@/services/factories/orders";

export const getOrderListItemsScenarioStore = (itemsNumber: number = 10) => {
  const list = OrderListItemFactory(itemsNumber);
  return {
    list,
  };
};
