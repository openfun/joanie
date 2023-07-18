import { render, screen } from "@testing-library/react";

import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CourseRunForm } from "@/components/templates/courses-runs/form/CourseRunForm";
import { CourseRunFactory } from "@/services/factories/courses-runs";

describe("<CourseRunForm/>", () => {
  it("renders an empty form ", async () => {
    render(
      <TestingWrapper>
        <CourseRunForm />
      </TestingWrapper>,
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

  it("renders a populated form", async () => {
    const courseRun = CourseRunFactory();
    render(
      <TestingWrapper>
        <CourseRunForm courseRun={courseRun} />
      </TestingWrapper>,
    );
    const title: HTMLInputElement = await screen.findByRole("textbox", {
      name: "Title",
    });
    expect(title.value).toBe(courseRun.title);
  });
});
