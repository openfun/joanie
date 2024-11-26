import type { CertificateDefinition } from "./CertificateDefinition";
import {
  DTOProductTargetCourseRelation,
  ProductTargetCourseRelation,
} from "./ProductTargetCourseRelation";
import { CourseProductRelation } from "./Relations";
import { Nullable, Optional, ToFormValues } from "@/types/utils";
import { ProductFormMainValues } from "@/components/templates/products/form/sections/main/ProductFormMain";
import { ContractDefinition } from "@/services/api/models/ContractDefinition";

export type BaseProduct = {
  id: string;
  type: ProductType;
  title: string;
  description?: string;
  call_to_action: string;
  price?: number;
  price_currency?: string;
  instructions?: string;
};

export type Product = BaseProduct & {
  target_courses?: ProductTargetCourseRelation[];
  course_relations?: CourseProductRelation[];
  contract_definition: Nullable<ContractDefinition>;
  certificate_definition: Nullable<CertificateDefinition>;
};

export type ProductSimple = BaseProduct & {
  target_courses?: string[];
  certificate_definition: Nullable<string>;
  course_relations?: string[];
  contract_definition: Nullable<string>;
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
  instructions?: string;
  price_currency?: string;
  certificate_definition?: Nullable<CertificateDefinition>;
  contract_definition?: Nullable<ContractDefinition>;
}>;

export type DTOProduct = {
  id?: string;
  type: ProductType;
  title: string;
  description?: string;
  instructions?: string;
  call_to_action: string;
  price?: number;
  price_currency?: string;
  certificate_definition?: string;
  contract_definition?: string;
};

export const transformProductToDTO = (
  product: Product | ProductFormMainValues,
): DTOProduct => {
  return {
    ...product,
    certificate_definition: product.certificate_definition?.id,
    contract_definition: product.contract_definition?.id,
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
    is_graded: target_course.is_graded ?? false,
    position: target_course.position ?? 0,
    course_runs: courseRuns ?? [],
  };
};
