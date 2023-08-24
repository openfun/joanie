import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { OrganizationForm } from "@/components/templates/organizations/form/OrganizationForm";
import { OrganizationFactory } from "@/services/factories/organizations";

describe("<OrganizationForm/>", () => {
  it("renders an empty form ", async () => {
    render(
      <TestingWrapper>
        <OrganizationForm />
      </TestingWrapper>,
    );

    await screen.findByRole("textbox", { name: "Title" });
    screen.getByRole("textbox", { name: "Code" });
    screen.getByRole("textbox", { name: "Representative" });
    screen.getByRole("button", { name: "Choose a logo" });
    screen.getByRole("button", { name: "Add a signature" });
    screen.getByRole("button", { name: "Submit" });
    expect(screen.queryByText("Organization members")).toBe(null);
  });
  it("renders a populated form", async () => {
    const org = OrganizationFactory();
    render(
      <TestingWrapper>
        <OrganizationForm organization={org} />
      </TestingWrapper>,
    );

    const title: HTMLInputElement = await screen.findByRole("textbox", {
      name: "Title",
    });
    expect(title.value).toBe(org.title);
    const code: HTMLInputElement = screen.getByRole("textbox", {
      name: "Code",
    });
    expect(code.value).toBe(org.code);
    if (org.accesses && org.accesses.length > 0) {
      await screen.findByText("Organization members");
      org.accesses.forEach((access) => {
        screen.getByText(access.user.username);
      });
    }
  });
});
