import { render, screen } from "@testing-library/react";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { CoursesRunsList } from "@/components/templates/courses-runs/list/CoursesRunsList";

describe("<CoursesRunsList/>", () => {
  it("renders a CoursesRunsList component ", async () => {
    await render(
      <TestingWrapper>
        <CoursesRunsList />
      </TestingWrapper>
    );

    await screen.findByText("Title");
    screen.getByText("Resource link");
    screen.getByText("Course start");
    screen.getByText("Course end");
    screen.getByText("State");
  });
});
