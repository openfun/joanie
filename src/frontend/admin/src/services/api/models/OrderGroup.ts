import { CourseProductRelation } from "@/services/api/models/Relations";

export type OrderGroup = {
  id: string;
  nb_available_seats: number;
  nb_seats: number;
  is_active: boolean;
  can_edit: boolean;
};

export type OrderGroupDummy = Omit<OrderGroup, "id"> & {
  dummyId?: string;
};

export type DTOOrderGroup = {
  nb_seats: OrderGroup["nb_seats"];
  is_active: OrderGroup["is_active"];
  course_product_relation: CourseProductRelation["id"];
};
