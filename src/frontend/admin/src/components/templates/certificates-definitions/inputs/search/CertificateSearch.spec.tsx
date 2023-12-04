import { render, screen } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { http, HttpResponse } from "msw";
import userEvent from "@testing-library/user-event";
import { server } from "../../../../../../mocks/server";
import { Nullable } from "@/types/utils";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { CertificateSearch } from "@/components/templates/certificates-definitions/inputs/search/CertificateSearch";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { buildApiUrl } from "@/services/http/HttpService";
import { certificateDefinitionRoutes } from "@/services/repositories/certificate-definition/CertificateDefinitionRepository";
import { CertificateDefinitionFactory } from "@/services/factories/certificate-definition";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";

interface Form {
  definition: Nullable<CertificateDefinition>;
}
describe("<CertificateSearch />", () => {
  function Wrapper({
    onSubmit,
    definition,
  }: {
    definition?: CertificateDefinition;
    onSubmit: (values: Form) => void;
  }) {
    const form = useForm<Form>({
      defaultValues: { definition: definition ?? null },
    });

    return (
      <RHFProvider
        methods={form}
        onSubmit={form.handleSubmit((values) => {
          onSubmit(values);
        })}
      >
        <CertificateSearch
          enableAdd
          enableEdit
          name="definition"
          label="definition"
        />
      </RHFProvider>
    );
  }

  const definition = CertificateDefinitionFactory();
  definition.title = "Testing";

  beforeEach(() => {
    server.use(
      http.get(buildApiUrl(certificateDefinitionRoutes.getAll()), () => {
        return HttpResponse.json([definition]);
      }),
    );
  });

  it("render and search", async () => {
    const onSubmit = jest.fn();
    render(<Wrapper onSubmit={onSubmit} />, { wrapper: TestingWrapper });
    const definitionSearch = await screen.findByRole("combobox", {
      name: "definition",
    });
    await userEvent.type(definitionSearch, "Tes");
    await userEvent.click(screen.getByText(definition.title));
    await userEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit).toBeCalledWith({ definition });
  });
  it("render and add", async () => {
    const onSubmit = jest.fn();
    render(<Wrapper onSubmit={onSubmit} />, { wrapper: TestingWrapper });
    const definitionSearch = await screen.findByRole("combobox", {
      name: "definition",
    });
    await userEvent.type(definitionSearch, "Tes");
    await userEvent.click(screen.getByText(definition.title));
    await userEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit).toBeCalledWith({ definition });
  });
});
