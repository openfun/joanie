import { Optional } from "@/types/utils";
import { ThumbnailDetailField } from "@/services/api/models/Image";
import { Accesses } from "@/services/api/models/Accesses";

export type Organization = {
  id: string;
  code: string;
  title: string;
  representative?: string;
  signature?: ThumbnailDetailField;
  logo?: ThumbnailDetailField;
  accesses?: Accesses<OrganizationRoles>[];
  country?: string;
  enterprise_code?: string; // SIRET in France
  activity_category_code?: string; // APE in France
  representative_profession?: string;
  signatory_representative?: string;
  signatory_representative_profession?: string;
  contact_phone?: string;
  contact_email?: string;
  dpo_email?: string;
  addresses?: OrganizationAddress[];
};

export type OrganizationAddress = {
  id: string;
  title: string;
  address: string;
  postcode: string;
  city: string;
  country: string;
  first_name: string;
  last_name: string;
  is_main: boolean;
  is_reusable: boolean;
};

export enum OrganizationRoles {
  OWNER = "owner",
  ADMIN = "administrator",
  MEMBER = "member",
}

export type DTOOrganization = Optional<
  Omit<Organization, "signature" | "logo" | "accesses">,
  "id"
> & {
  signature?: File;
  logo?: File;
};

export type DTOOrganizationAddress = Optional<
  Omit<OrganizationAddress, "id">,
  "is_reusable" | "is_main"
>;
