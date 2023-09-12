import { render } from "@testing-library/react";
import { CreateOrEditCertificationModal } from "@/components/templates/certificates-definitions/modals/CreateOrEditCertificationModal";
import { useModal } from "@/components/presentational/modal/useModal";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

describe("<CreateOrEditCertificationModal />", () => {
  function Wrapper() {
    const addModal = useModal();
    const afterSubmit = jest.fn();
    return (
      <CreateOrEditCertificationModal
        createModalUtils={addModal}
        afterSubmit={afterSubmit}
      />
    );
  }
  it("render and open addModal", async () => {
    render(<Wrapper />, { wrapper: TestingWrapper });
  });
});
