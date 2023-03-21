/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Course } from './Course';
import type { Organization } from './Organization';

export type CertificateOrder = {
  readonly id?: string;
  course?: Course;
  organization?: Organization;
};

