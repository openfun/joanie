import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { OrganizationForm } from "@/components/templates/organizations/form/OrganizationForm";
import { createDummyOrganization } from "@/services/factories/organizations/organizationFactory";

describe("<OrganizationForm/>", () => {
  it("renders a CourseRunForm component ", async () => {
    render(
      <TestingWrapper>
        <OrganizationForm />
      </TestingWrapper>
    );

    await screen.findByRole("textbox", { name: "Title" });
    screen.getByRole("textbox", { name: "Code" });
    screen.getByRole("textbox", { name: "Representative" });
    screen.getByRole("button", { name: "Choose a logo" });
    screen.getByRole("button", { name: "Add a signature" });
    screen.getByRole("button", { name: "Submit" });
  });
  it("renders a CourseRunForm component with organization", async () => {
    const org = createDummyOrganization();
    render(
      <TestingWrapper>
        <OrganizationForm organization={org} />
      </TestingWrapper>
    );

    const title: HTMLInputElement = await screen.findByRole("textbox", {
      name: "Title",
    });
    expect(title.value).toBe(org.title);
    const code: HTMLInputElement = screen.getByRole("textbox", {
      name: "Code",
    });
    expect(code.value).toBe(org.code);
  });
});
