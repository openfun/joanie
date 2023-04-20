import type { CertificateDefinition } from "./CertificateDefinition";
import { ProductTargetCourseRelation } from "./ProductTargetCourseRelation";
import { ProductRelationToCourse } from "./Relations";

export type Product = {
  id: string;
  type: ProductType;
  title: string;
  description?: string;
  call_to_action: string;
  target_courses?: ProductTargetCourseRelation[];
  price?: number;
  price_currency?: string;
  certificate_definitions?: CertificateDefinition;
  courses?: ProductRelationToCourse[];
};

export enum ProductType {
  CREDENTIAL = "credential",
  ENROLLMENT = "enrollment",
  CERTIFICATE = "certificate",
}
