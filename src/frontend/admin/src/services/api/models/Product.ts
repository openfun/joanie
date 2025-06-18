import type { CertificateDefinition } from "./CertificateDefinition";
import {
  DTOProductTargetCourseRelation,
  ProductTargetCourseRelation,
} from "./ProductTargetCourseRelation";
import { Offer } from "./Offers";
import { Maybe, Nullable, Optional, ToFormValues } from "@/types/utils";
import { ProductFormMainValues } from "@/components/templates/products/form/sections/main/ProductFormMain";
import { ContractDefinition } from "@/services/api/models/ContractDefinition";
import { Teacher } from "@/services/api/models/Teacher";
import { Skill } from "@/services/api/models/Skill";

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
  offers?: Offer[];
  contract_definition: Nullable<ContractDefinition>;
  certificate_definition: Nullable<CertificateDefinition>;
  certification_level: Nullable<number>;
  teachers: Teacher[];
  skills: Skill[];
};

export type ProductSimple = BaseProduct & {
  target_courses?: string[];
  certificate_definition: Nullable<string>;
  offers?: string[];
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
  price: number;
  instructions: string;
  price_currency: string;
  contract_definition: Nullable<ContractDefinition>;
}>;
export type ProductFormDefaultValues = {
  type: ProductType;
  title: string;
  description: string;
  call_to_action: string;
  target_courses?: ProductTargetCourseRelation[];
  price: Maybe<number>;
  instructions: string;
  price_currency: string;
  contract_definition: Nullable<ContractDefinition>;
};

export type ProductCertificationFormValues = {
  certificate_definition: Nullable<CertificateDefinition>;
  certification_level: Nullable<number>;
  teachers: Teacher[];
  skills: Skill[];
};

export type DTOProductCertification = {
  id: Product["id"];
  certificate_definition: Nullable<CertificateDefinition["id"]>;
  certification_level: Nullable<number>;
  teachers: Teacher["id"][];
  skills: Skill["id"][];
};

export type DTOProduct = {
  id?: string;
  type: ProductType;
  title: string;
  description?: string;
  instructions?: string;
  call_to_action: string;
  price?: number;
  price_currency?: string;
  contract_definition: Nullable<string>;
};

export const transformProductToDTO = (
  product: Product | ProductFormMainValues,
): DTOProduct => ({
  ...product,
  contract_definition: product.contract_definition?.id ?? null,
});

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

export const transformProductCertificationToDTO = (
  data: ProductCertificationFormValues & { id: Product["id"] },
): DTOProductCertification => ({
  id: data.id,
  certificate_definition: data.certificate_definition?.id ?? null,
  certification_level: data.certification_level ?? null,
  teachers: data.teachers.map((teacher) => teacher.id) ?? [],
  skills: data.skills.map((skill) => skill.id) ?? [],
});
