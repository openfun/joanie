/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { CertificationDefinition } from "./CertificationDefinition";
import { ProductTargetCourseRelation } from "./ProductTargetCourseRelation";
import { ProductRelationToCourse } from "./Relations";

export type Product = {
  id: string;
  type: Product.type;
  title: string;
  description?: string;
  call_to_action: string;
  target_courses?: ProductTargetCourseRelation[];
  price?: number;
  price_currency?: string;
  certificate_definitions?: CertificationDefinition;
  courses?: ProductRelationToCourse[];
};

export namespace Product {
  export enum type {
    CREDENTIAL = "credential",
    ENROLLMENT = "enrollment",
    CERTIFICATE = "certificate",
  }
}
