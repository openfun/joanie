import { BatchOrderFactory } from "@/services/factories/batch-orders";
import { User } from "@/services/api/models/User";
import { Organization } from "@/services/api/models/Organization";
import { Offering } from "@/services/api/models/Offerings";

export const getBatchOrdersScenarioStore = (itemsNumber: number = 30) => {
  const list = BatchOrderFactory(itemsNumber);
  const users: User[] = [];
  const organizations: Organization[] = [];
  const offerings: Offering[] = [];

  list.forEach((batchOrder) => {
    users.push(batchOrder.owner);
    if (batchOrder.organization) {
      organizations.push(batchOrder.organization);
    }
    offerings.push(batchOrder.offering);
  });

  return {
    list,
    users,
    organizations,
    offerings,
  };
};
