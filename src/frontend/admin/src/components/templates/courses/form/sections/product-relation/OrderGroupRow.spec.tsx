import { render, screen } from "@testing-library/react";
import { IntlProvider } from "react-intl";
import { OrderGroupRow } from "@/components/templates/courses/form/sections/product-relation/OrderGroupRow";

describe("<OrderGroupRow />", () => {
  it("renders available seats", async () => {
    const orderGroup = {
      id: "1",
      can_edit: true,
      nb_seats: 10,
      nb_available_seats: 5,
      is_active: true,
      discount: null,
    };

    render(
      <IntlProvider locale="en">
        <OrderGroupRow orderGroup={orderGroup} orderIndex={0} />
      </IntlProvider>,
    );

    screen.getByRole("heading", { name: /order group 1/i });
    screen.getByText("5/10 seats");
  });

  it("renders amount discount", async () => {
    const orderGroup = {
      id: "1",
      can_edit: true,
      nb_seats: null,
      nb_available_seats: null,
      is_active: true,
      discount: { id: "1", amount: 10, rate: null },
    };

    render(
      <IntlProvider locale="en">
        <OrderGroupRow orderGroup={orderGroup} orderIndex={0} />
      </IntlProvider>,
    );

    screen.getByRole("heading", { name: /order group 1/i });
    screen.getByText("Discount: 10 €");
  });

  it("renders rate discount", async () => {
    const orderGroup = {
      id: "1",
      can_edit: true,
      nb_seats: null,
      nb_available_seats: null,
      is_active: true,
      discount: { id: "1", amount: null, rate: 0.1 },
    };

    render(
      <IntlProvider locale="en">
        <OrderGroupRow orderGroup={orderGroup} orderIndex={0} />
      </IntlProvider>,
    );

    screen.getByRole("heading", { name: /order group 1/i });
    screen.getByText("Discount: 10%");
  });

  it("renders seats and discount", async () => {
    const orderGroup = {
      id: "1",
      can_edit: true,
      nb_seats: 10,
      nb_available_seats: 5,
      is_active: true,
      discount: { id: "1", amount: 10, rate: null },
    };

    render(
      <IntlProvider locale="en">
        <OrderGroupRow orderGroup={orderGroup} orderIndex={0} />
      </IntlProvider>,
    );

    screen.getByRole("heading", { name: /order group 1/i });
    screen.getByText("5/10 seats - Discount: 10 €");
  });
});
