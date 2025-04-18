import * as React from "react";
import Grid from "@mui/material/Grid2";
import Typography from "@mui/material/Typography";
import { useIntl } from "react-intl";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { RHFSelect } from "@/components/presentational/hook-form/RHFSelect";

export function ProductFormFinancial() {
  const intl = useIntl();
  return (
    <Grid container spacing={2}>
      <Grid size={12}>
        <Typography variant="subtitle2">
          {intl.formatMessage(productFormMessages.financialInformationTitle)}
        </Typography>
      </Grid>
      <Grid size={{ xs: 12, lg: 5 }}>
        <RHFTextField
          required
          name="call_to_action"
          label={intl.formatMessage(productFormMessages.callToAction)}
        />
      </Grid>
      <Grid size={{ xs: 12, md: 8, lg: 5 }}>
        <RHFTextField
          required
          type="number"
          slotProps={{ htmlInput: { min: 0, step: "0.01" } }}
          name="price"
          label={intl.formatMessage(productFormMessages.price)}
        />
      </Grid>
      <Grid size={{ xs: 12, md: 4, lg: 2 }}>
        <RHFSelect
          name="price_currency"
          label={intl.formatMessage(productFormMessages.priceCurrency)}
          options={[{ label: "Euro", value: "EUR" }]}
        />
      </Grid>
    </Grid>
  );
}
