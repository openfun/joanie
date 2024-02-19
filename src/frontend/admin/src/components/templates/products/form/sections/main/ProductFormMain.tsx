import * as React from "react";
import { useEffect } from "react";
import Grid from "@mui/material/Unstable_Grid2";
import Typography from "@mui/material/Typography";
import { useIntl } from "react-intl";
import IconButton from "@mui/material/IconButton";
import ModeEditOutlineTwoToneIcon from "@mui/icons-material/ModeEditOutlineTwoTone";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { RHFSelect } from "@/components/presentational/hook-form/RHFSelect";
import {
  Product,
  ProductFormValues,
  ProductType,
  transformProductToDTO,
} from "@/services/api/models/Product";
import { CertificateSearch } from "@/components/templates/certificates-definitions/inputs/search/CertificateSearch";
import { ProductFormFinancial } from "@/components/templates/products/form/sections/main/financial/ProductFormFinancial";
import { WizardStepProps } from "@/components/presentational/wizard/Wizard";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";
import { useProducts } from "@/hooks/useProducts/useProducts";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { ProductFormInstructions } from "@/components/templates/products/form/sections/main/instructions/ProductFormInstructions";
import { removeEOL } from "@/utils/string";
import { ContractDefinition } from "@/services/api/models/ContractDefinition";
import { ContractDefinitionSearch } from "@/components/templates/contract-definition/inputs/ContractDefinitionSearch";
import { TranslatableContent } from "@/components/presentational/translatable-content/TranslatableContent";

type Props = WizardStepProps & {
  product?: Product;
  fromProduct?: Product;
  productType?: ProductType;
  onResetType: () => void;
  afterSubmit?: (product: Product) => void;
};

const Schema = Yup.object().shape({
  title: Yup.string().required(),
  type: Yup.string<ProductType>().required(),
  description: Yup.string().required(),
  price: Yup.number().min(0.0).required(),
  price_currency: Yup.string().optional(),
  instructions: Yup.string().optional(),
  call_to_action: Yup.string().required(),
  certificate_definition: Yup.mixed<CertificateDefinition>()
    .nullable()
    .optional(),
  contract_definition: Yup.mixed<ContractDefinition>().nullable().optional(),
});

export type ProductFormMainValues = Omit<ProductFormValues, "target_courses">;

export function ProductFormMain({
  productType = ProductType.CREDENTIAL,
  product,
  fromProduct,
  afterSubmit,
  ...props
}: Props) {
  const intl = useIntl();
  const productRepository = useProducts({}, { enabled: false });
  const defaultProduct = product ?? fromProduct;
  const getDefaultValues = (): ProductFormMainValues => {
    return {
      title: defaultProduct?.title ?? "",
      type: defaultProduct?.type ?? ProductType.CERTIFICATE,
      description: removeEOL(defaultProduct?.description),
      price: defaultProduct?.price ?? 0,
      price_currency: defaultProduct?.price_currency ?? "EUR",
      call_to_action: defaultProduct?.call_to_action ?? "",
      certificate_definition: defaultProduct?.certificate_definition ?? null,
      instructions: removeEOL(defaultProduct?.instructions),
      contract_definition: defaultProduct?.contract_definition ?? null,
    };
  };

  const methods = useForm({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues() as any,
  });

  useEffect(() => {
    methods.reset(getDefaultValues());
  }, [product]);

  useEffect(() => {
    props.onValidate?.(methods.formState.isValid);
  }, [methods.formState.isValid]);

  useEffect(() => {
    methods.setValue("type", productType);
  }, [productType]);

  const onSubmit = (values: ProductFormMainValues): void => {
    const payload = transformProductToDTO({ id: product?.id, ...values });
    if (product) {
      productRepository.methods.update(payload, {
        onSuccess: (data) => {
          afterSubmit?.(data);
        },
      });
    } else {
      productRepository.methods.create(payload, {
        onSuccess: (data) => afterSubmit?.(data),
      });
    }
  };

  return (
    <TranslatableContent
      onSelectLang={() => {
        if (productRepository) productRepository.methods.invalidate();
      }}
    >
      <RHFProvider
        id="product-main-form"
        methods={methods}
        onSubmit={methods.handleSubmit(onSubmit)}
      >
        <Grid container spacing={2}>
          <Grid xs={12}>
            <Typography variant="subtitle2">
              {intl.formatMessage(productFormMessages.mainInformationTitle)}
            </Typography>
          </Grid>
          <Grid xs={12} md={6}>
            <RHFTextField
              required
              name="title"
              label={intl.formatMessage(commonTranslations.title)}
            />
          </Grid>
          <Grid xs={12} md={6}>
            <RHFSelect
              required
              leftIcons={
                <IconButton onClick={props.onResetType} size="small">
                  <ModeEditOutlineTwoToneIcon color="primary" />
                </IconButton>
              }
              data-testid="type-select"
              disabled
              name="type"
              label={intl.formatMessage(productFormMessages.productTypeLabel)}
              options={[
                {
                  label: ProductType.CERTIFICATE,
                  value: ProductType.CERTIFICATE,
                },
                {
                  label: ProductType.CREDENTIAL,
                  value: ProductType.CREDENTIAL,
                },
                {
                  label: ProductType.ENROLLMENT,
                  value: ProductType.ENROLLMENT,
                },
              ]}
            />
          </Grid>

          <Grid xs={12}>
            <RHFTextField
              name="description"
              required
              multiline
              minRows={3}
              label={intl.formatMessage(commonTranslations.description)}
            />
          </Grid>

          {productType !== ProductType.ENROLLMENT && (
            <Grid xs={12}>
              <CertificateSearch
                placeholder="search"
                enableAdd={true}
                helperText={intl.formatMessage(
                  productFormMessages.definitionHelper,
                )}
                enableEdit={true}
                name="certificate_definition"
                label={intl.formatMessage(productFormMessages.definition)}
              />
            </Grid>
          )}
          <Grid xs={12}>
            <ContractDefinitionSearch
              placeholder={intl.formatMessage(
                productFormMessages.contractDefinitionPlaceholder,
              )}
              enableAdd={true}
              helperText={intl.formatMessage(
                productFormMessages.contractDefinitionHelper,
              )}
              enableEdit={true}
              name="contract_definition"
              label={intl.formatMessage(productFormMessages.contractDefinition)}
            />
          </Grid>
        </Grid>
        <ProductFormFinancial />
        <ProductFormInstructions />
      </RHFProvider>
    </TranslatableContent>
  );
}
