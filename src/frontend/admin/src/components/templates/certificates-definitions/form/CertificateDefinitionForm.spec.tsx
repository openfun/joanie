import { render, screen } from "@testing-library/react";
import { IntlProvider } from "react-intl";
import { CertificateDefinitionForm } from "@/components/templates/certificates-definitions/form/CertificateDefinitionForm";

describe("<CertificateDefinitionForm/>", () => {
  it("renders a CertificateDefinitionForm component ", async () => {
    render(
      <IntlProvider locale="en">
        <CertificateDefinitionForm />
      </IntlProvider>
    );
    await screen.findByRole("textbox", { name: "Title" });
    screen.getByRole("textbox", { name: "Name" });
    screen.getByRole("textbox", { name: "Description" });
    screen.getByTestId("template-select");
    screen.getByRole("button", { name: "Submit" });
  });
});
