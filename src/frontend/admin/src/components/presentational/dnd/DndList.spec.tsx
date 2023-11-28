import { render, screen } from "@testing-library/react";
import { DndList } from "@/components/presentational/dnd/DndList";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

interface DummyRow {
  id: string;
  title: string;
}

interface DummyCreatingRow {
  dummyId?: string;
  title: string;
}

describe("<DndList />", () => {
  it("render a DndList component", async () => {
    const onSorted = jest.fn();
    const rows: DummyRow[] = [
      { id: "1", title: "John Doe" },
      { id: "2", title: "Alfred Teach" },
    ];

    const creatingRows: DummyCreatingRow[] = [
      { dummyId: "3", title: "Louis Albert" },
    ];

    render(
      <DndList<DummyRow, DummyCreatingRow>
        droppableId="test-drop"
        rows={rows}
        creatingRows={creatingRows}
        renderCreatingRow={(row) => (
          <div data-testid="creating-row">{row.item.title}</div>
        )}
        renderRow={(row) => <div data-testid="row">{row.item.title}</div>}
        onSorted={onSorted}
      />,
      { wrapper: TestingWrapper },
    );

    await screen.findByText("John Doe");
    screen.getByText("Alfred Teach");
    expect(screen.getAllByTestId("row").length).toBe(2);

    screen.getByText("Louis Albert");
    expect(screen.getAllByTestId("creating-row").length).toBe(1);
    expect(screen.getAllByTestId("dnd-loading").length).toBe(1);
  });
});
