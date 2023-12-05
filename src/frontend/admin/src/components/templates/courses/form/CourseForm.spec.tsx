import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CourseForm } from "@/components/templates/courses/form/CourseForm";
import { CourseFactory } from "@/services/factories/courses";

describe("<CourseForm/>", () => {
  it("renders", async () => {
    render(
      <TestingWrapper>
        <CourseForm />
      </TestingWrapper>,
    );

    await screen.findByText("Main information");
    screen.getByRole("textbox", { name: "Code" });
    screen.getByRole("textbox", { name: "Title" });
    screen.getByRole("combobox", { name: "Organizations" });

    screen.getByRole("button", { name: "Submit" });
    expect(screen.queryByText("Course members")).not.toBeInTheDocument();
  });

  it("renders  a populated form ", async () => {
    const course = CourseFactory();
    render(
      <TestingWrapper>
        <CourseForm course={course} />
      </TestingWrapper>,
    );
    const title: HTMLInputElement = await screen.findByRole("textbox", {
      name: "Title",
    });
    expect(title.value).toBe(course.title);

    const code: HTMLInputElement = screen.getByRole("textbox", {
      name: "Code",
    });
    screen.getByText("Relation to products");
    screen.getByRole("button", { name: "Add relation" });
    expect(code.value).toBe(course.code);
    if (course.accesses && course.accesses.length > 0) {
      await screen.findByText("Course members");
      course.accesses.forEach((access) => {
        screen.getByText(access.user.username);
      });
    }
  });

  it("renders a populated form without the product relation section", async () => {
    const course = CourseFactory();
    render(
      <TestingWrapper>
        <CourseForm course={course} showProductRelationSection={false} />
      </TestingWrapper>,
    );
    const title: HTMLInputElement = await screen.findByRole("textbox", {
      name: "Title",
    });
    expect(title.value).toBe(course.title);
    expect(screen.queryByText("Relation to products")).not.toBeInTheDocument();
  });
});
