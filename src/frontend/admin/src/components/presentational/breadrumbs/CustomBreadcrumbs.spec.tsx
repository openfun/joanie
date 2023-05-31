import { render, screen } from "@testing-library/react";
import { CustomBreadcrumbs } from "@/components/presentational/breadrumbs/CustomBreadcrumbs";

describe("<CustomBreadcrumb />", () => {
  it("renders", async () => {
    render(
      <CustomBreadcrumbs
        links={[
          { name: "Home" },
          { name: "Courses" },
          { name: "List", isActive: true },
        ]}
      />
    );
    await screen.findByText("Home");
    screen.getByText("Courses");

    const listIsActive = screen.getByText("List");
    expect(listIsActive).toHaveStyle("color: rgba(0, 0, 0, 0.87)");

    const separators = screen.getAllByLabelText("breadcrumb-separator");
    expect(separators.length).toEqual(2);
  });
});
