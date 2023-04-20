/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

export type CertificationDefinition = {
  id: string;
  name: string;
  title: string;
  description?: string;
  template?: string;
};

export interface DTOCertificationDefinition
  extends Omit<CertificationDefinition, "id"> {
  id?: string;
}
