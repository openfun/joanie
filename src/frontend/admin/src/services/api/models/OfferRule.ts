import { CourseProductRelation } from "@/services/api/models/Relations";
import { Discount } from "@/services/api/models/Discount";

export type OfferRule = {
  id: string;
  description: string | null;
  nb_available_seats: number | null;
  nb_seats: number | null;
  start: string | null;
  end: string | null;
  is_active: boolean;
  can_edit: boolean;
  discount: Discount | null;
};

export type OfferRuleDummy = Omit<OfferRule, "id"> & {
  dummyId?: string;
};

export type DTOOfferRule = {
  description?: OfferRule["description"];
  nb_seats?: OfferRule["nb_seats"];
  start?: OfferRule["start"];
  end?: OfferRule["end"];
  is_active: OfferRule["is_active"];
  course_product_relation: CourseProductRelation["id"];
  discount_id?: Discount["id"] | null;
};
