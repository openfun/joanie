import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CoursesList } from "@/components/templates/courses/list/CoursesList";

describe("<CoursesList/>", () => {
  it("renders a CoursesList component ", async () => {
    render(
      <TestingWrapper>
        <CoursesList />
      </TestingWrapper>
    );

    await screen.findByText("Code");
    screen.getByText("Title");
    screen.getByText("State");
  });
});
