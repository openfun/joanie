import * as React from "react";
import { ReactNode } from "react";
import { FormattedMessage, defineMessages, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import RemoveRedEyeIcon from "@mui/icons-material/RemoveRedEye";
import { useRouter } from "next/router";
import { useTheme } from "@mui/material/styles";
import { GridColDef } from "@mui/x-data-grid";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";
import { BatchOrder } from "@/services/api/models/BatchOrder";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { formatShortDate } from "@/utils/dates";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import {
  batchOrderPaymentMethodsMessages,
  batchOrderStatesMessages,
} from "@/components/templates/batch-orders/view/translations";
import { orderStatesMessages } from "@/components/templates/orders/view/translations";

const messages = defineMessages({
  sectionTitle: {
    id: "components.templates.batchOrders.view.sectionTitle",
    defaultMessage: "Batch Order informations",
    description: "Title for the batch order information section",
  },
  sectionAlert: {
    id: "components.templates.batchOrders.view.sectionAlert",
    defaultMessage:
      "In this view, you can see the details of a batch order, such as the company, seats, and status.",
    description: "Informative text for the batch order view",
  },
  organization: {
    id: "components.templates.batchOrders.view.organization",
    defaultMessage: "Organization",
    description: "Label for organization",
  },
  product: {
    id: "components.templates.batchOrders.view.product",
    defaultMessage: "Product",
    description: "Label for product",
  },
  course: {
    id: "components.templates.batchOrders.view.course",
    defaultMessage: "Course",
    description: "Label for course",
  },
  owner: {
    id: "components.templates.batchOrders.view.owner",
    defaultMessage: "Owner",
    description: "Label for owner",
  },
  companyName: {
    id: "components.templates.batchOrders.view.companyName",
    defaultMessage: "Company name",
    description: "Label for company name",
  },
  nbSeats: {
    id: "components.templates.batchOrders.view.nbSeats",
    defaultMessage: "Number of seats",
    description: "Label for number of seats",
  },
  state: {
    id: "components.templates.batchOrders.view.state",
    defaultMessage: "State",
    description: "Label for state",
  },
  total: {
    id: "components.templates.batchOrders.view.total",
    defaultMessage: "Total",
    description: "Label for total",
  },
  paymentMethod: {
    id: "components.templates.batchOrders.view.paymentMethod",
    defaultMessage: "Payment method",
    description: "Label for payment method",
  },
  purchaseOrderReference: {
    id: "components.templates.batchOrders.view.purchaseOrderReference",
    defaultMessage: "Purchase order reference",
    description: "Label for purchase order reference",
  },
  billingAddressTitle: {
    id: "components.templates.batchOrders.view.billingAddressTitle",
    defaultMessage: "Billing address",
    description: "Title for billing address section",
  },
  billingAddressCompanyName: {
    id: "components.templates.batchOrders.view.billingAddressCompanyName",
    defaultMessage: "Billing company name",
    description: "Label for billing address company name",
  },
  billingAddressIdentificationNumber: {
    id: "components.templates.batchOrders.view.billingAddressIdentificationNumber",
    defaultMessage: "Billing identification number",
    description: "Label for billing address identification number",
  },
  billingAddressContactName: {
    id: "components.templates.batchOrders.view.billingAddressContactName",
    defaultMessage: "Billing contact name",
    description: "Label for billing address contact name",
  },
  billingAddressContactEmail: {
    id: "components.templates.batchOrders.view.billingAddressContactEmail",
    defaultMessage: "Billing contact email",
    description: "Label for billing address contact email",
  },
  identificationNumber: {
    id: "components.templates.batchOrders.view.identificationNumber",
    defaultMessage: "Identification number",
    description: "Label for identification number",
  },
  vatRegistration: {
    id: "components.templates.batchOrders.view.vatRegistration",
    defaultMessage: "VAT registration",
    description: "Label for VAT registration",
  },
  address: {
    id: "components.templates.batchOrders.view.address",
    defaultMessage: "Address",
    description: "Label for address",
  },
  billingAddress: {
    id: "components.templates.batchOrders.view.billingAddress",
    defaultMessage: "Billing address",
    description: "Label for billing address field",
  },
  postcode: {
    id: "components.templates.batchOrders.view.postcode",
    defaultMessage: "Postcode",
    description: "Label for postcode",
  },
  billingPostcode: {
    id: "components.templates.batchOrders.view.billingPostcode",
    defaultMessage: "Billing postcode",
    description: "Label for billing postcode",
  },
  city: {
    id: "components.templates.batchOrders.view.city",
    defaultMessage: "City",
    description: "Label for city",
  },
  billingCity: {
    id: "components.templates.batchOrders.view.billingCity",
    defaultMessage: "Billing city",
    description: "Label for billing city",
  },
  country: {
    id: "components.templates.batchOrders.view.country",
    defaultMessage: "Country",
    description: "Label for country",
  },
  billingCountry: {
    id: "components.templates.batchOrders.view.billingCountry",
    defaultMessage: "Billing country",
    description: "Label for billing country",
  },
  administrativeContactTitle: {
    id: "components.templates.batchOrders.view.administrativeContactTitle",
    defaultMessage: "Administrative contact",
    description: "Title for administrative contact section",
  },
  administrativeFirstname: {
    id: "components.templates.batchOrders.view.administrativeFirstname",
    defaultMessage: "Administrative first name",
    description: "Label for administrative first name",
  },
  administrativeLastname: {
    id: "components.templates.batchOrders.view.administrativeLastname",
    defaultMessage: "Administrative last name",
    description: "Label for administrative last name",
  },
  administrativeProfession: {
    id: "components.templates.batchOrders.view.administrativeProfession",
    defaultMessage: "Administrative profession",
    description: "Label for administrative profession",
  },
  administrativeEmail: {
    id: "components.templates.batchOrders.view.administrativeEmail",
    defaultMessage: "Administrative email",
    description: "Label for administrative email",
  },
  administrativeTelephone: {
    id: "components.templates.batchOrders.view.administrativeTelephone",
    defaultMessage: "Administrative telephone",
    description: "Label for administrative telephone",
  },
  signatoryContactTitle: {
    id: "components.templates.batchOrders.view.signatoryContactTitle",
    defaultMessage: "Signatory contact",
    description: "Title for signatory contact section",
  },
  signatoryFirstname: {
    id: "components.templates.batchOrders.view.signatoryFirstname",
    defaultMessage: "Signatory first name",
    description: "Label for signatory first name",
  },
  signatoryLastname: {
    id: "components.templates.batchOrders.view.signatoryLastname",
    defaultMessage: "Signatory last name",
    description: "Label for signatory last name",
  },
  signatoryProfession: {
    id: "components.templates.batchOrders.view.signatoryProfession",
    defaultMessage: "Signatory profession",
    description: "Label for signatory profession",
  },
  signatoryEmail: {
    id: "components.templates.batchOrders.view.signatoryEmail",
    defaultMessage: "Signatory email",
    description: "Label for signatory email",
  },
  signatoryTelephone: {
    id: "components.templates.batchOrders.view.signatoryTelephone",
    defaultMessage: "Signatory telephone",
    description: "Label for signatory telephone",
  },
  fundingTitle: {
    id: "components.templates.batchOrders.view.fundingTitle",
    defaultMessage: "Funding",
    description: "Title for funding section",
  },
  fundingEntity: {
    id: "components.templates.batchOrders.view.fundingEntity",
    defaultMessage: "Funding entity",
    description: "Label for funding entity",
  },
  fundingAmount: {
    id: "components.templates.batchOrders.view.fundingAmount",
    defaultMessage: "Funding amount",
    description: "Label for funding amount",
  },
  ordersTitle: {
    id: "components.templates.batchOrders.view.ordersTitle",
    defaultMessage: "Orders",
    description: "Title for the orders section",
  },
  orderOwner: {
    id: "components.templates.batchOrders.view.orderOwner",
    defaultMessage: "Owner",
    description: "Label for order owner column",
  },
  orderState: {
    id: "components.templates.batchOrders.view.orderState",
    defaultMessage: "State",
    description: "Label for order state column",
  },
  orderCreatedOn: {
    id: "components.templates.batchOrders.view.orderCreatedOn",
    defaultMessage: "Created on",
    description: "Label for order created on column",
  },
  orderUpdatedOn: {
    id: "components.templates.batchOrders.view.orderUpdatedOn",
    defaultMessage: "Updated on",
    description: "Label for order updated on column",
  },
  orderVoucher: {
    id: "components.templates.batchOrders.view.orderVoucher",
    defaultMessage: "Voucher",
    description: "Label for order voucher column",
  },
});

export type Props = {
  batchOrder: BatchOrder;
};

export function BatchOrderView({ batchOrder }: Props) {
  const intl = useIntl();
  const router = useRouter();
  const theme = useTheme();
  const copyToClipboard = useCopyToClipboard();

  const getViewIcon = (url: string): ReactNode => {
    return (
      <Tooltip title={intl.formatMessage(commonTranslations.clickToView)}>
        <IconButton onClick={() => router.push(url)}>
          <RemoveRedEyeIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    );
  };

  return (
    <SimpleCard>
      <Box
        padding={8}
        sx={{
          ".MuiOutlinedInput-input.Mui-disabled": {
            textFillColor: theme.palette.text.primary,
          },
        }}
      >
        <Grid container spacing={2}>
          <Grid size={12}>
            <Typography variant="h6">
              <FormattedMessage {...messages.sectionTitle} />
            </Typography>
          </Grid>
          <Grid size={12}>
            <Alert severity="info">
              <FormattedMessage {...messages.sectionAlert} />
            </Alert>
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              InputProps={{
                ...(batchOrder.organization
                  ? {
                      endAdornment: getViewIcon(
                        PATH_ADMIN.organizations.edit(
                          batchOrder.organization.id,
                        ),
                      ),
                    }
                  : {}),
              }}
              label={intl.formatMessage(messages.organization)}
              value={batchOrder.organization?.title ?? ""}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              InputProps={{
                endAdornment: getViewIcon(
                  PATH_ADMIN.products.edit(batchOrder.offering.product.id),
                ),
              }}
              label={intl.formatMessage(messages.product)}
              value={batchOrder.offering.product.title}
            />
          </Grid>

          <Grid size={12}>
            {batchOrder.offering.course && (
              <TextField
                fullWidth={true}
                disabled={true}
                InputProps={{
                  endAdornment: getViewIcon(
                    PATH_ADMIN.courses.edit(batchOrder.offering.course.id),
                  ),
                }}
                label={intl.formatMessage(messages.course)}
                value={batchOrder.offering.course.title}
              />
            )}
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.owner)}
              helperText={
                <Tooltip
                  title={intl.formatMessage(commonTranslations.clickToCopy)}
                  onClick={() => copyToClipboard(batchOrder.owner.email)}
                >
                  <Typography sx={{ cursor: "pointer" }} variant="caption">
                    {batchOrder.owner.email}
                  </Typography>
                </Tooltip>
              }
              value={batchOrder.owner.full_name ?? batchOrder.owner.username}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.companyName)}
              value={batchOrder.company_name}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.nbSeats)}
              value={batchOrder.nb_seats}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.state)}
              value={intl.formatMessage(
                batchOrderStatesMessages[batchOrder.state],
              )}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              InputProps={{
                endAdornment: batchOrder.total_currency,
              }}
              label={intl.formatMessage(messages.total)}
              value={batchOrder.total}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.paymentMethod)}
              value={intl.formatMessage(
                batchOrderPaymentMethodsMessages[batchOrder.payment_method],
              )}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.identificationNumber)}
              value={batchOrder.identification_number}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.vatRegistration)}
              value={batchOrder.vat_registration ?? ""}
            />
          </Grid>

          <Grid size={12}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.address)}
              value={batchOrder.address}
            />
          </Grid>
          {batchOrder.quote?.purchase_order_reference && (
            <Grid size={12}>
              <TextField
                fullWidth={true}
                disabled={true}
                label={intl.formatMessage(messages.purchaseOrderReference)}
                value={batchOrder.quote?.purchase_order_reference}
              />
            </Grid>
          )}
          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.postcode)}
              value={batchOrder.postcode}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.city)}
              value={batchOrder.city}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.country)}
              value={batchOrder.country}
            />
          </Grid>

          {/* Billing Address Section */}
          <Grid size={12}>
            <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>
              <FormattedMessage {...messages.billingAddressTitle} />
            </Typography>
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.billingAddressCompanyName)}
              value={batchOrder.billing_address.company_name}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.billingAddressContactName)}
              value={batchOrder.billing_address.contact_name}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.billingAddressContactEmail)}
              value={batchOrder.billing_address.contact_email}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(
                messages.billingAddressIdentificationNumber,
              )}
              value={batchOrder.billing_address.identification_number}
            />
          </Grid>

          <Grid size={12}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.billingAddress)}
              value={batchOrder.billing_address.address}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.billingPostcode)}
              value={batchOrder.billing_address.postcode}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.billingCity)}
              value={batchOrder.billing_address.city}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 4 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.billingCountry)}
              value={batchOrder.billing_address.country}
            />
          </Grid>

          {/* Administrative Contact Section */}
          <Grid size={12}>
            <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>
              <FormattedMessage {...messages.administrativeContactTitle} />
            </Typography>
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.administrativeFirstname)}
              value={batchOrder.administrative_firstname}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.administrativeLastname)}
              value={batchOrder.administrative_lastname}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.administrativeProfession)}
              value={batchOrder.administrative_profession}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.administrativeEmail)}
              value={batchOrder.administrative_email}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.administrativeTelephone)}
              value={batchOrder.administrative_telephone}
            />
          </Grid>

          {/* Signatory Contact Section */}
          <Grid size={12}>
            <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>
              <FormattedMessage {...messages.signatoryContactTitle} />
            </Typography>
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.signatoryFirstname)}
              value={batchOrder.signatory_firstname}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.signatoryLastname)}
              value={batchOrder.signatory_lastname}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.signatoryProfession)}
              value={batchOrder.signatory_profession}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.signatoryEmail)}
              value={batchOrder.signatory_email}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.signatoryTelephone)}
              value={batchOrder.signatory_telephone}
            />
          </Grid>

          {/* Funding Section */}
          <Grid size={12}>
            <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>
              <FormattedMessage {...messages.fundingTitle} />
            </Typography>
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.fundingEntity)}
              value={batchOrder.funding_entity}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              InputProps={{
                endAdornment: batchOrder.total_currency,
              }}
              label={intl.formatMessage(messages.fundingAmount)}
              value={batchOrder.funding_amount}
            />
          </Grid>

          {/* Orders Section */}
          <Grid size={12}>
            <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>
              <FormattedMessage {...messages.ordersTitle} />
            </Typography>
            <TableComponent
              rows={batchOrder.orders}
              columns={getOrderColumns(intl)}
              disableRowSelectionOnClick
              hideFooterPagination={true}
              enableEdit={false}
            />
          </Grid>
        </Grid>
      </Box>
    </SimpleCard>
  );
}

function getOrderColumns(intl: ReturnType<typeof useIntl>): GridColDef[] {
  return [
    {
      field: "owner_name",
      headerName: intl.formatMessage(messages.orderOwner),
      flex: 1,
      renderCell: (cell) => (
        <CustomLink
          href={PATH_ADMIN.orders.view(cell.row.id)}
          title={intl.formatMessage(commonTranslations.view)}
        >
          {cell.row.owner_name}
        </CustomLink>
      ),
    },
    {
      field: "state",
      headerName: intl.formatMessage(messages.orderState),
      flex: 1,
      valueGetter: (value) => intl.formatMessage(orderStatesMessages[value]),
    },
    {
      field: "created_on",
      headerName: intl.formatMessage(messages.orderCreatedOn),
      flex: 1,
      valueGetter: (value, row) => formatShortDate(row.created_on),
    },
    {
      field: "updated_on",
      headerName: intl.formatMessage(messages.orderUpdatedOn),
      flex: 1,
      valueGetter: (value, row) => formatShortDate(row.updated_on),
    },
    {
      field: "voucher",
      headerName: intl.formatMessage(messages.orderVoucher),
      flex: 1,
    },
  ];
}
