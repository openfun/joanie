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
import { RHFCheckbox } from "@/components/presentational/hook-form/RHFCheckbox";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { OfferingSearch } from "@/components/templates/offerings/inputs/search/OfferingSearch";
import { Offering } from "@/services/api/models/Offerings";
import { Organization } from "@/services/api/models/Organization";
import { DTOOrderCreate, OrderListItem } from "@/services/api/models/Order";
import { useOrders } from "@/hooks/useOrders/useOrders";
import { useWaffleSwitch } from "@/hooks/useWaffle/useWaffle";

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
  fullDiscountLabel: {
    id: "components.templates.orders.form.fullDiscountLabel",
    defaultMessage: "Full discount (100%)",
    description:
      "Label for the full discount checkbox in the order create form",
  },
  discountSubtitle: {
    id: "components.templates.orders.form.discountSubtitle",
    defaultMessage: "Discount",
    description: "Subtitle of the discount section of the order create form",
  },
  discountValueLabel: {
    id: "components.templates.orders.form.discountValueLabel",
    defaultMessage: "Value",
    description: "Label for the discount value field in the order create form",
  },
  discountTypeLabel: {
    id: "components.templates.orders.form.discountTypeLabel",
    defaultMessage: "Type",
    description: "Label for the discount type field in the order create form",
  },
  discountTypeRate: {
    id: "components.templates.orders.form.discountTypeRate",
    defaultMessage: "Percentage",
    description: "Option label for percentage discount type",
  },
  discountTypeAmount: {
    id: "components.templates.orders.form.discountTypeAmount",
    defaultMessage: "Fixed amount",
    description: "Option label for fixed amount discount type",
  },
  discountValuePositiveError: {
    id: "components.templates.orders.form.discountValuePositiveError",
    defaultMessage: "Value must be greater than 0",
    description: "Error message when discount value is not a positive number",
  },
  discountRateMaxError: {
    id: "components.templates.orders.form.discountRateMaxError",
    defaultMessage: "Percentage must be between 1 and 100",
    description: "Error message when percentage discount is out of range",
  },
  discountAmountIntegerError: {
    id: "components.templates.orders.form.discountAmountIntegerError",
    defaultMessage: "Amount must be a positive whole number",
    description: "Error message when fixed amount discount is not an integer",
  },
});

type FormValues = {
  offering: Offering | null;
  organization: Organization | null;
  fullDiscount: boolean;
  discountType: "rate" | "amount";
  discountValue: number | "";
};

type Props = {
  afterSubmit?: (order: OrderListItem) => void;
};

export function OrderCreateForm({ afterSubmit }: Props) {
  const intl = useIntl();
  const customDiscountEnabled = useWaffleSwitch("admin_order_custom_discount");

  const RegisterSchema = Yup.object().shape({
    offering: Yup.mixed<Offering>().required(),
    organization: Yup.mixed<Organization>()
      .nullable()
      .when("offering", {
        is: (offering: Offering | null) =>
          !!offering && offering.organizations.length > 1,
        then: (schema) => schema.required(),
        otherwise: (schema) => schema.notRequired(),
      }),
    fullDiscount: Yup.boolean().required(),
    discountType: Yup.string().oneOf(["rate", "amount"]).required(),
    discountValue: Yup.mixed()
      .when("fullDiscount", {
        is: false,
        then: (schema) =>
          schema
            .required()
            .test(
              "is-positive",
              intl.formatMessage(messages.discountValuePositiveError),
              (value) => Number(value) > 0,
            ),
        otherwise: (schema) => schema.nullable(),
      })
      .when(["fullDiscount", "discountType"], {
        is: (fullDiscount: boolean, discountType: string) =>
          !fullDiscount && discountType === "rate",
        then: (schema) =>
          schema.test(
            "rate-max",
            intl.formatMessage(messages.discountRateMaxError),
            (value) => Number(value) <= 100,
          ),
      })
      .when(["fullDiscount", "discountType"], {
        is: (fullDiscount: boolean, discountType: string) =>
          !fullDiscount && discountType === "amount",
        then: (schema) =>
          schema.test(
            "amount-integer",
            intl.formatMessage(messages.discountAmountIntegerError),
            (value) => Number.isInteger(Number(value)),
          ),
      }),
  });
  const ordersQuery = useOrders({}, { enabled: false });

  const methods = useForm<FormValues>({
    resolver: yupResolver(RegisterSchema) as any,
    defaultValues: {
      offering: null,
      organization: null,
      fullDiscount: true,
      discountType: "amount",
      discountValue: "",
    },
  });

  const offering = useWatch({ control: methods.control, name: "offering" });
  const fullDiscount = useWatch({
    control: methods.control,
    name: "fullDiscount",
  });
  const multipleOrgs = offering !== null && offering.organizations.length > 1;

  useEffect(() => {
    if (offering && offering.organizations.length === 1) {
      methods.setValue("organization", offering.organizations[0]);
    } else {
      methods.setValue("organization", null);
    }
  }, [offering]);

  const onSubmit = (values: FormValues) => {
    const payload: DTOOrderCreate = {
      product_id: values.offering!.product.id,
      course_code: values.offering!.course.code,
      organization_id: values.organization?.id ?? null,
    };

    if (!values.fullDiscount && values.discountValue !== "") {
      payload.discount_type = values.discountType;
      payload.discount_value = Number(values.discountValue);
    }

    ordersQuery.methods.create(payload, {
      onSuccess: (data) => afterSubmit?.(data),
    });
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
                SelectProps={{
                  renderValue: (value: any) => value?.title ?? "",
                }}
              />
            </Grid>
          )}

          {customDiscountEnabled && (
            <>
              <Grid size={12}>
                <Typography variant="subtitle2">
                  {intl.formatMessage(messages.discountSubtitle)}
                </Typography>
              </Grid>

              <Grid size={12}>
                <RHFCheckbox
                  name="fullDiscount"
                  label={intl.formatMessage(messages.fullDiscountLabel)}
                />
              </Grid>

              {!fullDiscount && (
                <>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <RHFTextField
                      name="discountValue"
                      type="number"
                      label={intl.formatMessage(messages.discountValueLabel)}
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <RHFSelect
                      name="discountType"
                      label={intl.formatMessage(messages.discountTypeLabel)}
                      options={[
                        {
                          label: intl.formatMessage(messages.discountTypeRate),
                          value: "rate",
                        },
                        {
                          label: intl.formatMessage(
                            messages.discountTypeAmount,
                          ),
                          value: "amount",
                        },
                      ]}
                    />
                  </Grid>
                </>
              )}
            </>
          )}
        </Grid>
      </RHFProvider>
    </Box>
  );
}
