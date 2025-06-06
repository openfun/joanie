import { render, screen } from "@testing-library/react";
import { IntlProvider } from "react-intl";
import { OfferRuleRow } from "@/components/templates/courses/form/sections/product-relation/OfferRuleRow";

describe("<OfferRuleRow />", () => {
  it("renders available seats", async () => {
    const offerRule = {
      id: "1",
      can_edit: true,
      nb_seats: 10,
      nb_available_seats: 5,
      start: null,
      end: null,
      is_active: true,
      discount: null,
    };

    render(
      <IntlProvider locale="en">
        <OfferRuleRow offerRule={offerRule} orderIndex={0} />
      </IntlProvider>,
    );

    screen.getByRole("heading", { name: /offer rule 1/i });
    screen.getByText("5/10 seats");
  });

  it("renders amount discount", async () => {
    const offerRule = {
      id: "1",
      can_edit: true,
      nb_seats: null,
      nb_available_seats: null,
      start: null,
      end: null,
      is_active: true,
      discount: { id: "1", amount: 10, rate: null },
    };

    render(
      <IntlProvider locale="en">
        <OfferRuleRow offerRule={offerRule} orderIndex={0} />
      </IntlProvider>,
    );

    screen.getByRole("heading", { name: /offer rule 1/i });
    screen.getByText("Discount: 10 €");
  });

  it("renders rate discount", async () => {
    const offerRule = {
      id: "1",
      can_edit: true,
      nb_seats: null,
      nb_available_seats: null,
      start: null,
      end: null,
      is_active: true,
      discount: { id: "1", amount: null, rate: 0.1 },
    };

    render(
      <IntlProvider locale="en">
        <OfferRuleRow offerRule={offerRule} orderIndex={0} />
      </IntlProvider>,
    );

    screen.getByRole("heading", { name: /offer rule 1/i });
    screen.getByText("Discount: 10%");
  });

  it("renders start date", async () => {
    const offerRule = {
      id: "1",
      can_edit: true,
      nb_seats: null,
      nb_available_seats: null,
      start: "2025-04-01T00:00:00Z",
      end: null,
      is_active: true,
      discount: null,
    };

    render(
      <IntlProvider locale="en">
        <OfferRuleRow offerRule={offerRule} orderIndex={0} />
      </IntlProvider>,
    );

    screen.getByRole("heading", { name: /offer rule 1/i });
    screen.getByText("From: 4/1/25, 2:00 AM");
  });

  it("renders end date", async () => {
    const offerRule = {
      id: "1",
      can_edit: true,
      nb_seats: null,
      nb_available_seats: null,
      start: null,
      end: "2025-04-09T22:00:00Z",
      is_active: true,
      discount: null,
    };

    render(
      <IntlProvider locale="en">
        <OfferRuleRow offerRule={offerRule} orderIndex={0} />
      </IntlProvider>,
    );

    screen.getByRole("heading", { name: /offer rule 1/i });
    screen.getByText("To: 4/10/25, 12:00 AM");
  });
});
