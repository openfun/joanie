import * as React from "react";
import * as Yup from "yup";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Grid2";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { defineMessages, useIntl } from "react-intl";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFSelect } from "@/components/presentational/hook-form/RHFSelect";
import { OfferingSearch } from "@/components/templates/offerings/inputs/search/OfferingSearch";
import { Offering } from "@/services/api/models/Offerings";
import { Organization } from "@/services/api/models/Organization";
import { OrderListItem } from "@/services/api/models/Order";
import { useOrders } from "@/hooks/useOrders/useOrders";

const messages = defineMessages({
  generalSubtitle: {
    id: "components.templates.orders.form.generalSubtitle",
    defaultMessage: "General information",
    description: "Subtitle of the general section of the order create form",
  },
  offeringLabel: {
    id: "components.templates.orders.form.offeringLabel",
    defaultMessage: "Offering",
    description: "Label for the offering field in the order create form",
  },
  organizationLabel: {
    id: "components.templates.orders.form.organizationLabel",
    defaultMessage: "Organization",
    description: "Label for the organization field in the order create form",
  },
});

type FormValues = {
  offering: Offering | null;
  organization: Organization | null;
};

type Props = {
  afterSubmit?: (order: OrderListItem) => void;
};

const RegisterSchema = Yup.object().shape({
  offering: Yup.mixed<Offering>().required().nullable(),
  organization: Yup.mixed<Organization>().required().nullable(),
});

export function OrderCreateForm({ afterSubmit }: Props) {
  const intl = useIntl();
  const ordersQuery = useOrders({}, { enabled: false });

  const methods = useForm<FormValues>({
    resolver: yupResolver(RegisterSchema) as any,
    defaultValues: {
      offering: null,
      organization: null,
    },
  });

  const offering = useWatch({ control: methods.control, name: "offering" });
  const multipleOrgs = offering !== null && offering.organizations.length > 1;

  useEffect(() => {
    if (offering && offering.organizations.length === 1) {
      methods.setValue("organization", offering.organizations[0]);
    } else {
      methods.setValue("organization", null);
    }
  }, [offering]);

  const onSubmit = (values: FormValues) => {
    ordersQuery.methods.create(
      {
        product_id: values.offering!.product.id,
        course_code: values.offering!.course.code,
        organization_id: values.organization?.id ?? null,
      },
      {
        onSuccess: (data) => afterSubmit?.(data),
      },
    );
  };

  return (
    <Box padding={4}>
      <RHFProvider
        checkBeforeUnload={true}
        showSubmit={true}
        methods={methods}
        id="order-create-form"
        onSubmit={methods.handleSubmit(onSubmit)}
      >
        <Grid container spacing={2}>
          <Grid size={12}>
            <Typography variant="subtitle2">
              {intl.formatMessage(messages.generalSubtitle)}
            </Typography>
          </Grid>

          <Grid size={{ xs: 12, md: multipleOrgs ? 6 : 12 }}>
            <OfferingSearch
              name="offering"
              label={intl.formatMessage(messages.offeringLabel)}
            />
          </Grid>

          {multipleOrgs && (
            <Grid size={{ xs: 12, md: 6 }}>
              <RHFSelect
                name="organization"
                label={intl.formatMessage(messages.organizationLabel)}
                options={offering.organizations.map((org) => ({
                  label: org.title,
                  value: org,
                }))}
              />
            </Grid>
          )}
        </Grid>
      </RHFProvider>
    </Box>
  );
}
