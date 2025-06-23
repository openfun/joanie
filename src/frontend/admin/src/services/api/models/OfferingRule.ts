import { Offering } from "@/services/api/models/Offerings";
import { Discount } from "@/services/api/models/Discount";

export type OfferingRule = {
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

export type OfferingRuleDummy = Omit<OfferingRule, "id"> & {
  dummyId?: string;
};

export type DTOOfferingRule = {
  description?: OfferingRule["description"];
  nb_seats?: OfferingRule["nb_seats"];
  start?: OfferingRule["start"];
  end?: OfferingRule["end"];
  is_active: OfferingRule["is_active"];
  offering: Offering["id"];
  discount_id?: Discount["id"] | null;
};
