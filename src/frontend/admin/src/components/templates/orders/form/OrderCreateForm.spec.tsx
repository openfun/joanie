import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import * as React from "react";
import userEvent from "@testing-library/user-event";
import { server } from "mocks/server";
import { OfferingFactory } from "@/services/api/models/Offerings";
import { OrganizationFactory } from "@/services/factories/organizations";
import { OrderFactory } from "@/services/factories/orders";
import { buildApiUrl } from "@/services/http/HttpService";
import { offeringsRoutes } from "@/services/repositories/offering/OfferingRepository";
import { orderRoutes } from "@/services/repositories/orders/OrderRepository";
import { OrderCreateForm } from "@/components/templates/orders/form/OrderCreateForm";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

describe("<OrderCreateForm />", () => {
  const singleOrgOffering = OfferingFactory();
  singleOrgOffering.product.title = "Single Org Product";
  singleOrgOffering.course.title = "Single Org Course";
  singleOrgOffering.organizations = [OrganizationFactory()];

  const multiOrgOffering = OfferingFactory();
  multiOrgOffering.product.title = "Multi Org Product";
  multiOrgOffering.course.title = "Multi Org Course";
  multiOrgOffering.organizations = [
    OrganizationFactory(),
    OrganizationFactory(),
  ];
  multiOrgOffering.organizations[0].title = "Org Alpha";
  multiOrgOffering.organizations[1].title = "Org Beta";

  beforeEach(() => {
    server.use(
      http.get(buildApiUrl(offeringsRoutes.getAll()), () => {
        return HttpResponse.json({
          count: 2,
          results: [singleOrgOffering, multiOrgOffering],
          next: null,
          previous: null,
        });
      }),
      http.get(buildApiUrl(orderRoutes.getAll()), () => {
        return HttpResponse.json({
          count: 0,
          results: [],
          next: null,
          previous: null,
        });
      }),
    );
  });

  it("renders the offering search field and submit button", async () => {
    render(<OrderCreateForm />, { wrapper: TestingWrapper });
    await screen.findByRole("combobox", { name: "Offering" });
    screen.getByRole("button", { name: "Submit" });
  });

  it("does not show organization select when offering has a single organization", async () => {
    render(<OrderCreateForm />, { wrapper: TestingWrapper });
    const combobox = await screen.findByRole("combobox", { name: "Offering" });
    await userEvent.click(combobox);
    await userEvent.click(
      await screen.findByText("Single Org Product — Single Org Course"),
    );
    expect(screen.queryByLabelText("Organization")).not.toBeInTheDocument();
  });

  it("shows organization select when offering has multiple organizations", async () => {
    render(<OrderCreateForm />, { wrapper: TestingWrapper });
    const combobox = await screen.findByRole("combobox", { name: "Offering" });
    await userEvent.click(combobox);
    await userEvent.click(
      await screen.findByText("Multi Org Product — Multi Org Course"),
    );
    await screen.findByLabelText("Organization");
  });

  it("calls afterSubmit with the created order on successful submission", async () => {
    const createdOrder = OrderFactory();
    server.use(
      http.post(buildApiUrl(orderRoutes.create()), () => {
        return HttpResponse.json(createdOrder, { status: 201 });
      }),
    );

    const afterSubmit = jest.fn();
    render(<OrderCreateForm afterSubmit={afterSubmit} />, {
      wrapper: TestingWrapper,
    });

    const combobox = await screen.findByRole("combobox", { name: "Offering" });
    await userEvent.click(combobox);
    await userEvent.click(
      await screen.findByText("Single Org Product — Single Org Course"),
    );
    await userEvent.click(screen.getByRole("button", { name: "Submit" }));

    await screen.findByRole("button", { name: "Submit" });
    expect(afterSubmit).toHaveBeenCalledWith(createdOrder);
  });
});
