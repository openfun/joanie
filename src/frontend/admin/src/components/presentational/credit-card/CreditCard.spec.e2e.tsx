import { expect, test } from "@playwright/experimental-ct-react";
import CreditCard from "./CreditCard";
import { CreditCardFactory } from "@/services/factories/credit-cards";
import { toDigitString } from "@/utils/numbers";

test.describe("<CreditCard/>", () => {
  test("should render properly", async ({ mount }) => {
    const creditCard = CreditCardFactory({ brand: "visa" });
    const component = await mount(<CreditCard {...creditCard} />);

    // A label should be displayed
    await expect(component.getByText("Payment method")).toBeVisible();

    // The credit card brand logo should be displayed
    const brandSrc = await component.getByRole("img").getAttribute("src");
    expect(brandSrc).toEqual("/images/credit-card-brands/visa.svg");

    // Last numbers should be displayed
    const lastNumbers = component.getByText(creditCard.last_numbers);
    await expect(lastNumbers).toBeVisible();

    // Expiration date should be displayed
    const expirationDate = component.getByText(
      `${toDigitString(creditCard.expiration_month)} / ${creditCard.expiration_year}`,
      { exact: true },
    );
    await expect(expirationDate).toBeVisible();
  });

  test("should render expired credit card", async ({ mount }) => {
    const creditCard = CreditCardFactory({
      brand: "visa",
      expiration_year: 2023,
    });
    const component = await mount(<CreditCard {...creditCard} />);

    // Expiration date should be displayed suffixed with "Expired"
    const expirationDate = component.getByText(
      `${toDigitString(creditCard.expiration_month)} / ${creditCard.expiration_year} (Expired)`,
      { exact: true },
    );
    await expect(expirationDate).toBeVisible();
  });
});
