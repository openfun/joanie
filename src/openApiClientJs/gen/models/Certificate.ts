/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { CertificateOrder } from './CertificateOrder';
import type { CertificationDefinition } from './CertificationDefinition';

export type Certificate = {
  readonly id?: string;
  certificate_definition?: CertificationDefinition;
  readonly issued_on?: string;
  order?: CertificateOrder;
};

