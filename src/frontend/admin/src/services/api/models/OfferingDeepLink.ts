import { Offering } from "@/services/api/models/Offerings";
import { Organization } from "@/services/api/models/Organization";

export type OfferingDeepLink = {
  id: string;
  deep_link: string;
  is_active: boolean;
  offering: Offering["id"];
  organization: Organization["id"];
};

export type DTOCreateOfferingDeepLink = {
  organization_id: Organization["id"];
  deep_link: OfferingDeepLink["deep_link"];
};

export type DTOUpdateOfferingDeepLink = {
  organization?: Organization["id"];
  deep_link?: OfferingDeepLink["deep_link"];
  is_active?: OfferingDeepLink["is_active"];
};

export type OfferingDeepLinkDummy = Omit<OfferingDeepLink, "id"> & {
  dummyId?: string;
};
