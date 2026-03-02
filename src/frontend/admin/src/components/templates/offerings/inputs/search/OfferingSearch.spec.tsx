import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import * as React from "react";
import userEvent from "@testing-library/user-event";
import { useForm } from "react-hook-form";
import { server } from "mocks/server";
import { OfferingFactory } from "@/services/api/models/Offerings";
import { buildApiUrl } from "@/services/http/HttpService";
import { offeringsRoutes } from "@/services/repositories/offering/OfferingRepository";
import { OfferingSearch } from "@/components/templates/offerings/inputs/search/OfferingSearch";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";

const offering = OfferingFactory();
offering.product.title = "Test Product";
offering.course.title = "Test Course";

describe("<OfferingSearch />", () => {
  beforeEach(() => {
    server.use(
      http.get(buildApiUrl(offeringsRoutes.getAll()), () => {
        return HttpResponse.json({
          count: 1,
          results: [offering],
          next: null,
          previous: null,
        });
      }),
    );
  });

  function Wrapper() {
    const methods = useForm({ defaultValues: { offering: null } });
    return (
      <RHFProvider methods={methods} onSubmit={methods.handleSubmit(() => {})}>
        <OfferingSearch name="offering" label="Offering" />
      </RHFProvider>
    );
  }

  it("loads and displays offerings on mount", async () => {
    render(<Wrapper />, { wrapper: TestingWrapper });
    const combobox = await screen.findByRole("combobox", { name: "Offering" });
    await userEvent.click(combobox);
    await screen.findByText("Test Product — Test Course");
  });

  it("filters offerings by typing", async () => {
    render(<Wrapper />, { wrapper: TestingWrapper });
    const combobox = await screen.findByRole("combobox", { name: "Offering" });
    await userEvent.type(combobox, "Test");
    await screen.findByText("Test Product — Test Course");
  });
});
