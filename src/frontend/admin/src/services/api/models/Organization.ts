import { Optional } from "@/types/utils";
import { ThumbnailDetailField } from "@/services/api/models/Image";

export type Organization = {
  id: string;
  code: string;
  title: string;
  representative?: string;
  signature?: ThumbnailDetailField;
  logo?: ThumbnailDetailField;
};

export type DTOOrganization = Optional<
  Omit<Organization, "signature" | "logo">,
  "id"
> & {
  signature?: File;
  logo?: File;
};
