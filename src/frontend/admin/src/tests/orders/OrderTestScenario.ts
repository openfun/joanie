import { OrderFactory } from "@/services/factories/orders";
import { ProductSimple } from "@/services/api/models/Product";
import { User } from "@/services/api/models/User";
import { Organization } from "@/services/api/models/Organization";
import { Course } from "@/services/api/models/Course";

export const getOrdersScenarioStore = (itemsNumber: number = 30) => {
  const list = OrderFactory(itemsNumber);
  const products: ProductSimple[] = [];
  const users: User[] = [];
  const organizations: Organization[] = [];
  const courses: Course[] = [];

  list.forEach((order) => {
    products.push(order.product);
    users.push(order.owner);
    if (order.organization) {
      organizations.push(order.organization);
    }
    if (order.course) {
      courses.push(order.course);
    }
  });

  return {
    list,
    products,
    users,
    organizations,
    courses,
  };
};
