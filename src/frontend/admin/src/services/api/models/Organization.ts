/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import { File as CustomFile } from "./File";

export type Organization = {
  id: string;
  code: string;
  title: string;
  representative?: string;
  signature?: CustomFile;
  logo?: CustomFile;
};

export interface DTOOrganization
  extends Omit<Organization, "id" | "signature" | "logo"> {
  id?: string;
  signature?: File;
  logo?: File;
}
