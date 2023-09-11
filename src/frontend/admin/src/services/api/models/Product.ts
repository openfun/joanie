import type { CertificateDefinition } from "./CertificateDefinition";
import {
  DTOProductTargetCourseRelation,
  ProductTargetCourseRelation,
} from "./ProductTargetCourseRelation";
import { ProductRelationToCourse } from "./Relations";
import { Nullable, Optional, ToFormValues } from "@/types/utils";
import { ProductFormMainValues } from "@/components/templates/products/form/sections/main/ProductFormMain";

export type Product = {
  id: string;
  type: ProductType;
  title: string;
  description?: string;
  call_to_action: string;
  target_courses?: ProductTargetCourseRelation[];
  price?: number;
  price_currency?: string;
  certificate_definition?: CertificateDefinition;
  courses?: ProductRelationToCourse[];
};

export enum ProductType {
  CREDENTIAL = "credential",
  ENROLLMENT = "enrollment",
  CERTIFICATE = "certificate",
}

export type ProductFormValues = ToFormValues<{
  type: ProductType;
  title: string;
  description: string;
  call_to_action: string;
  target_courses?: ProductTargetCourseRelation[];
  price?: number;
  price_currency?: string;
  certificate_definition?: Nullable<CertificateDefinition>;
}>;

export type DTOProduct = {
  id?: string;
  type: ProductType;
  title: string;
  description?: string;
  call_to_action: string;
  price?: number;
  price_currency?: string;
  certificate_definition?: string;
};

export const transformProductToDTO = (
  product: Product | ProductFormMainValues,
): DTOProduct => {
  return {
    ...product,
    certificate_definition: product.certificate_definition?.id,
  };
};

export const transformProductTargetCourseRelationToDTO = (
  target_course: Optional<ProductTargetCourseRelation, "id">,
): DTOProductTargetCourseRelation => {
  const courseRuns = target_course.course_runs?.map(
    (course_run) => course_run.id,
  );

  return {
    ...(target_course.id && { id: target_course.id }),
    course: target_course.course?.id,
    graded: target_course.graded ?? false,
    position: target_course.position ?? 0,
    course_runs: courseRuns ?? [],
  };
};
