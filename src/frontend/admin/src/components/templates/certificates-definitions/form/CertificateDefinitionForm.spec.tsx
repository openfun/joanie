import { render, screen } from "@testing-library/react";
import { CertificateDefinitionForm } from "@/components/templates/certificates-definitions/form/CertificateDefinitionForm";
import { CertificateDefinitionFactory } from "@/services/factories/certificate-definition";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

describe("<CertificateDefinitionForm/>", () => {
  it("renders an empty form ", async () => {
    render(
      <TestingWrapper>
        <CertificateDefinitionForm />
      </TestingWrapper>,
    );
    await screen.findByRole("textbox", { name: "Title" });
    screen.getByRole("textbox", { name: "Name" });
    screen.getByRole("textbox", { name: "Description" });
    screen.getByTestId("template-select");
    screen.getByRole("button", { name: "Submit" });
  });

  it("renders  a populated form ", async () => {
    const definition = CertificateDefinitionFactory();
    render(
      <TestingWrapper>
        <CertificateDefinitionForm definition={definition} />
      </TestingWrapper>,
    );
    const title: HTMLInputElement = await screen.findByRole("textbox", {
      name: "Title",
    });
    expect(title.value).toBe(definition.title);

    const name: HTMLInputElement = screen.getByRole("textbox", {
      name: "Name",
    });
    expect(name.value).toBe(definition.name);

    const description: HTMLInputElement = screen.getByRole("textbox", {
      name: "Description",
    });
    expect(description.value).toBe(definition.description);
  });
});
