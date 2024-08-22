/**
 * Test suite for the CreditCardBrandLogo component
 */

import { render, screen } from "@testing-library/react";
import CreditCardBrandLogo from "./CreditCardBrandLogo";

describe("CreditCardBrandLogo", () => {
  it("should render the logo of a known credit card brand", () => {
    render(<CreditCardBrandLogo brand="visa" />);

    const img = screen.getByAltText("visa");
    expect(img).toBeInstanceOf(HTMLImageElement);
    expect(img).toHaveAttribute("src", "/images/credit-card-brands/visa.svg");
  });

  it("should render a credit card icon if the credit card brand is unknown", () => {
    render(<CreditCardBrandLogo brand="unknown-brand" />);

    screen.getByTestId("CreditCardIcon");
  });
});
