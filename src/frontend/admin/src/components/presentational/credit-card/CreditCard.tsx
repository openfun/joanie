import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import { useMemo } from "react";
import Divider from "@mui/material/Divider";
import { defineMessages, FormattedMessage } from "react-intl";
import CreditCardBrandLogo from "@/components/presentational/credit-card-brand-logo/CreditCardBrandLogo";
import { OrderCreditCard } from "@/services/api/models/Order";
import { toDigitString } from "@/utils/numbers";

type Props = OrderCreditCard;

const messages = defineMessages({
  paymentMethod: {
    id: "components.presentational.card.CreditCard.paymentMethod",
    defaultMessage: "Payment method",
    description: "Payment method label",
  },
  expired: {
    id: "components.presentational.card.CreditCard.expired",
    defaultMessage: "Expired",
    description: "Expired label",
  },
});

function CreditCard(props: Props) {
  const hasExpired = useMemo(() => {
    const currentYear = new Date().getFullYear();
    const currentMonth = new Date().getMonth() + 1;

    return (
      props.expiration_year < currentYear ||
      (props.expiration_year === currentYear &&
        props.expiration_month < currentMonth)
    );
  }, [props.expiration_month, props.expiration_year]);

  return (
    <Box
      border={1}
      borderColor={hasExpired ? "error.main" : "action.disabled"}
      borderRadius={1}
      position="relative"
      px={2}
      py={2}
      mt={1}
      maxWidth={480}
      data-testid={`credit-card-${props.id}`}
    >
      <Typography
        position="absolute"
        top="0"
        left="0"
        paddingX={0.5}
        sx={{ translate: "9px -50%" }}
        bgcolor="background.paper"
        color={hasExpired ? "error" : "text.disabled"}
        variant="caption"
      >
        <FormattedMessage {...messages.paymentMethod} />
      </Typography>
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <CreditCardBrandLogo brand={props.brand} />
        <Typography variant="subtitle1" fontWeight="bold" component="strong">
          ••••&nbsp;••••&nbsp;••••&nbsp;{props.last_numbers}
        </Typography>
        <Divider orientation="vertical" flexItem />
        <Typography
          variant="overline"
          color={hasExpired ? "error" : "text.secondary"}
          lineHeight={1}
        >
          {toDigitString(props.expiration_month)} / {props.expiration_year}
          {hasExpired && (
            <>
              {" "}
              (<FormattedMessage {...messages.expired} />)
            </>
          )}
        </Typography>
      </Stack>
    </Box>
  );
}

export default CreditCard;
