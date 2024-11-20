import { render, screen } from "@testing-library/react";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";

describe("<SimpleCard />", () => {
  it("renders", async () => {
    render(
      <SimpleCard>
        <div>Hello !</div>
      </SimpleCard>,
    );

    screen.getByText("Hello !");
  });
});
