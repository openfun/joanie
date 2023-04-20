import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CourseProductRelationForm } from "@/components/templates/courses/form/product-relation/CourseProductRelationForm";

describe("<CourseProductRelationForm/>", () => {
  it("renders ", async () => {
    render(
      <TestingWrapper>
        <CourseProductRelationForm />
      </TestingWrapper>
    );

    await screen.findByText("Product");
    screen.getByRole("combobox", { name: "Choose your product" });
    screen.findByText("Managed by this organizations");
    screen.getByRole("combobox", { name: "Search organization" });
    screen.getByRole("button", { name: "Submit" });
  });
});
