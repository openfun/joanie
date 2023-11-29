import { render, screen } from "@testing-library/react";

import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CourseRunForm } from "@/components/templates/courses-runs/form/CourseRunForm";
import { CourseRunFactory } from "@/services/factories/courses-runs";

// Mock useAllLanguages hook to get immediately languages list,
// in this way CourseRunForm default values are properly sets
jest.mock("@/hooks/useAllLanguages/useAllLanguages", () => ({
  __esModule: true,
  useAllLanguages: () => [
    { value: "en", display_name: "English" },
    { value: "fr", display_name: "French" },
    { value: "es", display_name: "Spanish" },
  ],
}));

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

    screen.getByRole("checkbox", { name: "Is gradable?" });
    screen.getByRole("checkbox", { name: "Is listed?" });
  });

  it("renders a populated form", async () => {
    const courseRun = CourseRunFactory();

    render(
      <TestingWrapper>
        <CourseRunForm courseRun={courseRun} />
      </TestingWrapper>,
    );

    const title: HTMLInputElement = screen.getByRole("textbox", {
      name: "Title",
    });
    expect(title.value).toBe(courseRun.title);

    const resourceLink: HTMLInputElement = screen.getByRole("textbox", {
      name: "Resource link",
    });
    expect(resourceLink.value).toBe(courseRun.resource_link);

    // We are using custom mui select with chips, we are not able to retrieve
    // the value as a regular select. We have to check that all expected chips has been rendered
    const languages = document.querySelectorAll("span.MuiChip-label");
    expect(languages).toHaveLength(courseRun.languages.length);

    const start: HTMLInputElement = screen.getByRole("textbox", {
      name: "Start",
    });
    expect(new Date(start.value).toISOString()).toBe(courseRun.start);

    const end: HTMLInputElement = screen.getByRole("textbox", { name: "End" });
    expect(new Date(end.value).toISOString()).toBe(courseRun.end);

    const enrollmentStart: HTMLInputElement = screen.getByRole("textbox", {
      name: "Enrollment start",
    });
    expect(new Date(enrollmentStart.value).toISOString()).toBe(
      courseRun.enrollment_start,
    );

    const enrollmentEnd: HTMLInputElement = screen.getByRole("textbox", {
      name: "Enrollment end",
    });
    expect(new Date(enrollmentEnd.value).toISOString()).toBe(
      courseRun.enrollment_end,
    );

    const isGradable: HTMLInputElement = screen.getByRole("checkbox", {
      name: "Is gradable?",
    });
    expect(isGradable.checked).toBe(courseRun.is_gradable);

    const isListed: HTMLInputElement = screen.getByRole("checkbox", {
      name: "Is listed?",
    });
    expect(isListed.checked).toBe(courseRun.is_listed);
  });
});
