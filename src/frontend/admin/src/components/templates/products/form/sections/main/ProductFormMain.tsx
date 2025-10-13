import * as React from "react";
import { useEffect } from "react";
import Grid from "@mui/material/Grid2";
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
  ProductFormDefaultValues,
  ProductFormValues,
  ProductType,
  transformProductToDTO,
} from "@/services/api/models/Product";
import { ProductFormFinancial } from "@/components/templates/products/form/sections/main/financial/ProductFormFinancial";
import {
  useWizardContext,
  WizardStepProps,
} from "@/components/presentational/wizard/Wizard";
import { useProducts } from "@/hooks/useProducts/useProducts";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { ProductFormInstructions } from "@/components/templates/products/form/sections/main/instructions/ProductFormInstructions";
import { removeEOL } from "@/utils/string";
import { ContractDefinition } from "@/services/api/models/ContractDefinition";
import { QuoteDefinition } from "@/services/api/models/QuoteDefinition";
import { ContractDefinitionSearch } from "@/components/templates/contract-definition/inputs/ContractDefinitionSearch";
import { QuoteDefinitionSearch } from "@/components/templates/quote-definition/inputs/QuoteDefinitionSearch";
import { TranslatableForm } from "@/components/presentational/translatable-content/TranslatableForm";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { useFormSubmit } from "@/hooks/form/useFormSubmit";

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
  price_currency: Yup.string().required(),
  instructions: Yup.string().defined(),
  call_to_action: Yup.string().required(),
  contract_definition_order: Yup.mixed<ContractDefinition>()
    .nullable()
    .defined(),
  contract_definition_batch_order: Yup.mixed<ContractDefinition>()
    .nullable()
    .defined(),
  quote_definition: Yup.mixed<QuoteDefinition>().nullable().defined(),
});

export type ProductFormMainValues = Omit<
  ProductFormValues,
  "certificate_definition" | "target_courses"
>;

export function ProductFormMain({
  productType = ProductType.CREDENTIAL,
  product,
  fromProduct,
  afterSubmit,
  ...props
}: Props) {
  const intl = useIntl();
  const formSubmitProps = useFormSubmit(product);
  const wizardContext = useWizardContext();
  const productRepository = useProducts({}, { enabled: false });
  const defaultProduct = product ?? fromProduct;
  const getDefaultValues = (): ProductFormDefaultValues => ({
    title: defaultProduct?.title ?? "",
    type: defaultProduct?.type ?? productType,
    description: removeEOL(defaultProduct?.description),
    price: defaultProduct?.price,
    price_currency: defaultProduct?.price_currency ?? "EUR",
    call_to_action: defaultProduct?.call_to_action ?? "",
    instructions: removeEOL(defaultProduct?.instructions),
    contract_definition_order:
      defaultProduct?.contract_definition_order ?? null,
    contract_definition_batch_order:
      defaultProduct?.contract_definition_batch_order ?? null,
    quote_definition: defaultProduct?.quote_definition ?? null,
  });

  const methods = useForm<ProductFormMainValues>({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues(),
  });

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

  useEffect(() => {
    const { isDirty } = methods.formState;
    wizardContext.setIsValidStep(
      !isDirty,
      isDirty ? intl.formatMessage(commonTranslations.formIsDirty) : "",
    );
  }, [methods.formState.isDirty]);

  useEffect(() => {
    props.onValidate?.(methods.formState.isValid);
  }, [methods.formState.isValid]);

  useEffect(() => {
    methods.setValue("type", productType);
  }, [productType]);

  return (
    <TranslatableForm
      resetForm={() => methods.reset(getDefaultValues())}
      entitiesDeps={[product]}
      onSelectLang={() => {
        if (productRepository) productRepository.methods.invalidate();
      }}
    >
      <RHFProvider
        id="product-main-form"
        checkBeforeUnload={true}
        showSubmit={formSubmitProps.showSubmit}
        methods={methods}
        onSubmit={methods.handleSubmit(onSubmit)}
      >
        <RHFValuesChange
          autoSave={formSubmitProps.enableAutoSave}
          onSubmit={onSubmit}
        >
          <Grid container spacing={2}>
            <Grid size={12}>
              <Typography variant="subtitle2">
                {intl.formatMessage(productFormMessages.mainInformationTitle)}
              </Typography>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <RHFTextField
                required
                name="title"
                label={intl.formatMessage(commonTranslations.title)}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
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

            <Grid size={12}>
              <RHFTextField
                name="description"
                required
                multiline
                minRows={3}
                label={intl.formatMessage(commonTranslations.description)}
              />
            </Grid>
            <Grid size={12}>
              <ContractDefinitionSearch
                placeholder={intl.formatMessage(
                  productFormMessages.contractDefinitionOrderPlaceholder,
                )}
                enableAdd={true}
                helperText={intl.formatMessage(
                  productFormMessages.contractDefinitionOrderHelper,
                )}
                enableEdit={true}
                name="contract_definition_order"
                label={intl.formatMessage(
                  productFormMessages.contractDefinitionOrder,
                )}
              />
              <ContractDefinitionSearch
                placeholder={intl.formatMessage(
                  productFormMessages.contractDefinitionBatchOrderPlaceholder,
                )}
                enableAdd={true}
                helperText={intl.formatMessage(
                  productFormMessages.contractDefinitionBatchOrderHelper,
                )}
                enableEdit={true}
                name="contract_definition_batch_order"
                label={intl.formatMessage(
                  productFormMessages.contractDefinitionBatchOrder,
                )}
              />
              <QuoteDefinitionSearch
                placeholder={intl.formatMessage(
                  productFormMessages.quoteDefinitionPlaceholder,
                )}
                enableAdd={true}
                helperText={intl.formatMessage(
                  productFormMessages.quoteDefinitionHelper,
                )}
                enableEdit={true}
                name="quote_definition"
                label={intl.formatMessage(productFormMessages.quoteDefinition)}
              />
            </Grid>
          </Grid>
          <ProductFormFinancial />
          <ProductFormInstructions />
        </RHFValuesChange>
      </RHFProvider>
    </TranslatableForm>
  );
}
