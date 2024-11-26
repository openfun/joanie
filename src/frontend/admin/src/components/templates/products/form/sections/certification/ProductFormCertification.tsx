import Grid from "@mui/material/Grid2";
import Alert from "@mui/material/Alert";
import { useIntl } from "react-intl";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import TeachersField from "./TeachersField";
import SkillsField from "./SkillsField";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";
import {
  Product,
  ProductCertificationFormValues,
  transformProductCertificationToDTO,
} from "@/services/api/models/Product";
import { Skill } from "@/services/api/models/Skill";
import { Teacher } from "@/services/api/models/Teacher";
import { CertificateSearch } from "@/components/templates/certificates-definitions/inputs/search/CertificateSearch";
import { TranslatableForm } from "@/components/presentational/translatable-content/TranslatableForm";
import { useProducts } from "@/hooks/useProducts/useProducts";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { useFormSubmit } from "@/hooks/form/useFormSubmit";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";

const FORM_VALIDATION_SCHEMA = Yup.object().shape({
  certificate_definition: Yup.mixed<CertificateDefinition>()
    .nullable()
    .defined(),
  certification_level: Yup.number()
    .integer()
    .min(1)
    .max(8)
    .nullable()
    .transform((val) => val || null)
    .defined(),
  teachers: Yup.array().of(Yup.mixed<Teacher>().defined()).defined(),
  skills: Yup.array().of(Yup.mixed<Skill>().defined()).defined(),
});

type ProductCertificationFormProps = {
  product: Product;
};

function ProductFormCertification({ product }: ProductCertificationFormProps) {
  const intl = useIntl();
  const formSubmitProps = useFormSubmit(product);
  const productRepository = useProducts({}, { enabled: false });
  const defaultValues: ProductCertificationFormValues = {
    certificate_definition: product?.certificate_definition ?? null,
    certification_level: product?.certification_level,
    teachers: product.teachers,
    skills: product.skills,
  };
  const methods = useForm({
    resolver: yupResolver(FORM_VALIDATION_SCHEMA),
    defaultValues,
  });

  const onSubmit = (values: ProductCertificationFormValues) => {
    const payload = transformProductCertificationToDTO({
      id: product.id,
      ...values,
    });
    productRepository.methods.update(payload);
  };

  return (
    <TranslatableForm
      resetForm={() => methods.reset(defaultValues)}
      entitiesDeps={[product]}
      onSelectLang={productRepository.methods.invalidate}
    >
      <RHFProvider
        id="product-certification-form"
        methods={methods}
        onSubmit={methods.handleSubmit(onSubmit)}
        showSubmit={formSubmitProps.showSubmit}
      >
        <RHFValuesChange
          autoSave={formSubmitProps.enableAutoSave}
          onSubmit={onSubmit}
        >
          <Grid container spacing={2}>
            <Grid size={12}>
              <Alert severity="info">
                {intl.formatMessage(
                  productFormMessages.productCertificationFormInfo,
                )}
              </Alert>
            </Grid>
            <Grid size={12} mt={3}>
              <Grid size={12}>
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
              {product.certificate_definition !== null && (
                <>
                  <Grid container spacing={2} mt={3}>
                    <Grid size={12}>
                      <Typography variant="subtitle2">
                        {intl.formatMessage(
                          productFormMessages.certificationDetailTitle,
                        )}
                      </Typography>
                    </Grid>
                    <Grid size={12}>
                      <RHFTextField
                        type="number"
                        slotProps={{ htmlInput: { min: 1, max: 8 } }}
                        name="certification_level"
                        label={intl.formatMessage(
                          productFormMessages.certificationLevelLabel,
                        )}
                        helperText={intl.formatMessage(
                          productFormMessages.certificationLevelHelper,
                        )}
                      />
                    </Grid>
                  </Grid>
                  <Stack spacing={2} mt={3}>
                    <TeachersField product={product} />
                  </Stack>
                  <Stack spacing={2} mt={3}>
                    <SkillsField product={product} />
                  </Stack>
                </>
              )}
            </Grid>
          </Grid>
        </RHFValuesChange>
      </RHFProvider>
    </TranslatableForm>
  );
}

export default ProductFormCertification;
