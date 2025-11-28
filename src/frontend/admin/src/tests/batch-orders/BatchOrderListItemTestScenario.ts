import { BatchOrderListItemFactory } from "@/services/factories/batch-orders";

export const getBatchOrderListItemsScenarioStore = (
  itemsNumber: number = 10,
) => {
  const list = BatchOrderListItemFactory(itemsNumber);
  return {
    list,
  };
};
