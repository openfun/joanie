import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { OrganizationsList } from "@/components/templates/organizations/list/OrganizationsList";

describe("<OrganizationsList/>", () => {
  it("renders a OrganizationsList component ", async () => {
    render(
      <TestingWrapper>
        <OrganizationsList />
      </TestingWrapper>
    );

    await screen.findByText("Code");
    screen.getByText("Title");
  });
});
