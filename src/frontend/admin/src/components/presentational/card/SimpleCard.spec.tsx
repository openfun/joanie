import { render, screen } from "@testing-library/react";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";

describe("<SimpleCard />", () => {
  it("renders", async () => {
    render(
      <SimpleCard>
        <div>Hello !</div>
      </SimpleCard>
    );

    const simpleCard = await screen.findByTestId("simpleCard");
    expect(simpleCard).toHaveStyle(
      "box-shadow: rgb(145 158 171 / 20%) 0px 0px 2px 0px,rgb(145 158 171 / 12%) 0px 12px 24px -4px"
    );

    screen.getByText("Hello !");
  });
});
