import { OrderFactory } from "@/services/factories/orders";

export const getOrdersScenarioStore = (itemsNumber: number = 30) => {
  const list = OrderFactory(itemsNumber);

  return {
    list,
  };
};
