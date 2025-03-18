import { CourseProductRelation } from "@/services/api/models/Relations";
import { Discount } from "@/services/api/models/Discount";

export type OrderGroup = {
  id: string;
  nb_available_seats: number | null;
  nb_seats: number | null;
  is_active: boolean;
  can_edit: boolean;
  discount: Discount | null;
};

export type OrderGroupDummy = Omit<OrderGroup, "id"> & {
  dummyId?: string;
};

export type DTOOrderGroup = {
  nb_seats?: OrderGroup["nb_seats"] | null;
  is_active: OrderGroup["is_active"];
  course_product_relation: CourseProductRelation["id"];
  discount_id?: Discount["id"] | null;
};
