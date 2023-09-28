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
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { ProductFormInstructions } from "@/components/templates/products/form/sections/main/instructions/ProductFormInstructions";

type Props = WizardStepProps & {
  product?: Product;
  productType?: ProductType;
  onResetType: () => void;
  afterSubmit?: (product: Product) => void;
};

const Schema = Yup.object().shape({
  title: Yup.string().required(),
  type: Yup.string<ProductType>().required(),
  description: Yup.string().required(),
  price: Yup.number().min(0).optional(),
  price_currency: Yup.string().optional(),
  instructions: Yup.string().optional(),
  call_to_action: Yup.string().required(),
  certificate_definition: Yup.mixed<CertificateDefinition>()
    .nullable()
    .optional(),
});

export type ProductFormMainValues = Omit<ProductFormValues, "target_courses">;

export function ProductFormMain({
  productType = ProductType.CREDENTIAL,
  product,
  afterSubmit,
  ...props
}: Props) {
  const intl = useIntl();
  const productRepository = useProducts({}, { enabled: false });

  const getDefaultValues = (): ProductFormMainValues => {
    return {
      title: product?.title ?? "",
      type: product?.type ?? ProductType.CERTIFICATE,
      description: product?.description ?? "",
      price: product?.price ?? 0,
      price_currency: product?.price_currency ?? "EUR",
      call_to_action: product?.call_to_action ?? "",
      certificate_definition: product?.certificate_definition ?? null,
      instructions: product?.instructions ?? "",
    };
  };

  const methods = useForm({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues(),
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
    <RHFProvider id="product-main-form" showSubmit={false} methods={methods}>
      <RHFValuesChange<ProductFormMainValues>
        onSubmit={(values) => onSubmit(values)}
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
        </Grid>
        <ProductFormFinancial />
        <ProductFormInstructions />
      </RHFValuesChange>
    </RHFProvider>
  );
}
