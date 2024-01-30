import { Optional, ToFormValues } from "@/types/utils";

export type CertificateDefinition = {
  id: string;
  name: string;
  title: string;
  description?: string;
  template?: string;
};

export type DTOCertificateDefinition = Optional<CertificateDefinition, "id">;

export type CertificateDefinitionFormValues = ToFormValues<
  Omit<CertificateDefinition, "id">
>;

export enum CertificationDefinitionTemplate {
  CERTIFICATE = "certificate",
  DEGREE = "degree",
}
