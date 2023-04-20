import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FileThumbnail } from "@/components/presentational/files/thumbnail/FileThumbnail";

describe("<FileThumbnail />", () => {
  it("renders", async () => {
    const user = userEvent.setup();
    const onDelete = jest.fn();
    const file = new File([new ArrayBuffer(40)], "file.jpg");
    render(<FileThumbnail file={file} onDelete={onDelete} />);

    await screen.findByText("file.jpg");
    screen.getByText("40 Bytes");

    const deleteButton = screen.getByRole("button", {
      name: "file-thumbnail-delete-button",
    });

    await user.click(deleteButton);
    expect(onDelete).toHaveBeenCalled();
  });
});
