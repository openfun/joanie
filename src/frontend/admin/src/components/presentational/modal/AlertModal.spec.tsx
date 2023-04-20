import { render, screen } from "@testing-library/react";
import { IntlProvider } from "react-intl";
import userEvent from "@testing-library/user-event";
import {
  AlertModal,
  AlertModalProps,
} from "@/components/presentational/modal/AlertModal";

describe("<AlertModal />", () => {
  function Modal(props: Partial<AlertModalProps>) {
    return (
      <IntlProvider locale="en">
        <AlertModal
          message="Hello !"
          handleAccept={props.handleAccept ?? (() => {})}
          title="Alert modal testing"
          open={true}
          handleClose={props.handleClose ?? (() => {})}
          {...props}
        />
      </IntlProvider>
    );
  }

  it("renders a AlertModal component ", async () => {
    render(<Modal />);
    await screen.findByText("Hello !");
    screen.getByText("Alert modal testing");
  });

  it("renders a AlertModal component and use custom CTA to validate button", async () => {
    render(<Modal validateLabel="Accept" />);
    await screen.findByText("Accept");
  });

  it("renders a AlertModal and click cancel button ", async () => {
    const user = userEvent.setup();
    const accept = jest.fn();
    const handleClose = jest.fn();
    render(<Modal handleClose={handleClose} handleAccept={accept} />);

    const cancelButton = await screen.findByText("Cancel");
    await user.click(cancelButton);
    expect(handleClose).toHaveBeenCalled();
  });
  it("renders a AlertModal and click accept button ", async () => {
    const user = userEvent.setup();
    const accept = jest.fn();
    const handleClose = jest.fn();
    render(<Modal handleClose={handleClose} handleAccept={accept} />);

    const validateButton = await screen.findByText("Validate");
    await user.click(validateButton);
    expect(accept).toHaveBeenCalled();
    expect(handleClose).toHaveBeenCalled();
  });
});
