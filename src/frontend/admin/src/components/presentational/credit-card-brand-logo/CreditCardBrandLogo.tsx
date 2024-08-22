import { CreditCard } from "@mui/icons-material";

enum SupportedCreditCardBrands {
  VISA = "visa",
  MASTERCARD = "mastercard",
  MAESTRO = "maestro",
}

function CreditCardBrandLogo({ brand }: { brand: string }) {
  const normalizedBrand = brand.toLowerCase();

  if (
    Object.values<string>(SupportedCreditCardBrands).includes(normalizedBrand)
  ) {
    return (
      <img
        src={`/images/credit-card-brands/${normalizedBrand}.svg`}
        alt={normalizedBrand}
        height="32"
      />
    );
  }

  return <CreditCard color="primary" fontSize="large" />;
}

export default CreditCardBrandLogo;
