import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CertificatesDefinitionsList } from "@/components/templates/certificates-definitions/list/CertificatesDefinitionsList";

describe("<CertificatesDefinitionsList/>", () => {
  it("renders a CertificatesDefinitionsList component ", async () => {
    render(
      <TestingWrapper>
        <CertificatesDefinitionsList />
      </TestingWrapper>,
    );

    await screen.findByText("Name");
    screen.getByText("Title");
  });
});
