import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CourseForm } from "@/components/templates/courses/form/CourseForm";
import { CourseFactory } from "@/services/factories/courses";

describe("<CourseForm/>", () => {
  it("renders", async () => {
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

  it("renders  a populated form ", async () => {
    const course = CourseFactory();
    render(
      <TestingWrapper>
        <CourseForm course={course} />
      </TestingWrapper>
    );
    const title: HTMLInputElement = await screen.findByRole("textbox", {
      name: "Title",
    });
    expect(title.value).toBe(course.title);

    const code: HTMLInputElement = screen.getByRole("textbox", {
      name: "Code",
    });
    expect(code.value).toBe(course.code);
  });
});
