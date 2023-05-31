import { Optional } from "@/types/utils";

export type CertificateDefinition = {
  id: string;
  name: string;
  title: string;
  description?: string;
  template?: string;
};

export type DTOCertificateDefinition = Optional<CertificateDefinition, "id">;
