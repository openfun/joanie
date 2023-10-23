import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { ContractsDefinitionsList } from "@/components/templates/contract-definition/list/ContractsDefinitionsList";

describe("<ContractDefinitionsList/>", () => {
  it("renders a ContractDefinitionsList component ", async () => {
    render(
      <TestingWrapper>
        <ContractsDefinitionsList />
      </TestingWrapper>,
    );

    await screen.findByText("Language");
    screen.getByText("Title");
  });
});
