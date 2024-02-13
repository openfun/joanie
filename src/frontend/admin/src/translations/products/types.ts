import { defineMessages } from "react-intl";
import { ProductType } from "@/services/api/models/Product";

export const productTypesMessages = defineMessages<ProductType>({
  [ProductType.CERTIFICATE]: {
    id: "translations.products.productTypesMessages.certificate",
    defaultMessage: "Certificate",
    description: "Label for the CERTIFICATE product type",
  },
  [ProductType.CREDENTIAL]: {
    id: "translations.products.productTypesMessages.credential",
    defaultMessage: "Credential",
    description: "Label for the CREDENTIAL product type",
  },
  [ProductType.ENROLLMENT]: {
    id: "translations.products.productTypesMessages.enrollment",
    defaultMessage: "Enrollment",
    description: "Label for the ENROLLMENT product type",
  },
});
