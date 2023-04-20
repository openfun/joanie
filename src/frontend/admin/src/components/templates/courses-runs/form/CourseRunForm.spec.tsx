import { render, screen } from "@testing-library/react";

import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CourseRunForm } from "@/components/templates/courses-runs/form/CourseRunForm";

describe("<CourseRunForm/>", () => {
  it("renders a CourseRunForm component ", async () => {
    render(
      <TestingWrapper>
        <CourseRunForm />
      </TestingWrapper>
    );
    await screen.findByText("General");
    screen.getByRole("textbox", { name: "Title" });
    screen.getByRole("textbox", { name: "Resource link" });
    screen.getByRole("combobox", { name: "Language" });

    screen.getByText("Course run dates");
    screen.getByRole("textbox", { name: "Start" });
    screen.getByRole("textbox", { name: "End" });

    screen.getByText("Enrollment dates");
    screen.getByRole("textbox", { name: "Enrollment start" });
    screen.getByRole("textbox", { name: "Enrollment end" });
  });
});
