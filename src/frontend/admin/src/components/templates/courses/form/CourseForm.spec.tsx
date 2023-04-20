import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CourseForm } from "@/components/templates/courses/form/CourseForm";

describe("<OrganizationForm/>", () => {
  it("renders a CourseRunForm component ", async () => {
    render(
      <TestingWrapper>
        <CourseForm />
      </TestingWrapper>
    );

    await screen.findByText("Main information");
    screen.getByRole("textbox", { name: "Code" });
    screen.getByRole("textbox", { name: "Title" });
    screen.getByRole("combobox", { name: "Organizations" });
    screen.getByText("Relation to products");
    screen.getByRole("button", { name: "Add relation" });
    screen.getByRole("button", { name: "Submit" });
  });
});
