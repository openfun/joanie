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
