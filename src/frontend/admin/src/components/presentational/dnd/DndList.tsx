import * as React from "react";
import { useState } from "react";
import { DragDropContext, DropResult } from "react-beautiful-dnd";
import { Box } from "@mui/material";
import { StrictModeDroppable } from "@/components/presentational/dnd/StrictModeDroppable";
import { DndItem } from "@/components/presentational/dnd/DndItem";

export interface Row {
  id?: string;
}

export interface RowPropsExtended<T> {
  item: T;
}

export interface DndListProps<TRowProps extends Row> {
  droppableId: string;
  disableDnd?: boolean;
  rows: TRowProps[];
  renderRow: (item: TRowProps, index: number) => React.ReactNode;
  onSorted: (items: TRowProps[]) => void;

  headerActions?: React.ReactNode;
}

export function DndList<TRowProps extends Row>({
  ...props
}: DndListProps<TRowProps>) {
  const onDragEnd = (result: DropResult) => {
    const { destination, source } = result;
    const newItems = [...props.rows];
    if (destination && source) {
      const old = newItems.splice(source.index, 1);
      newItems.splice(destination.index, 0, ...old);
    }

    props.onSorted(newItems);
  };

  return (
    <Box>
      {props.headerActions}
      <DragDropContext onDragEnd={onDragEnd}>
        <StrictModeDroppable droppableId={props.droppableId}>
          {(provided, snapshot) => (
            <div {...provided.droppableProps} ref={provided.innerRef}>
              {props.rows.map((item, index) => (
                <DndItem
                  isDisabled={props.disableDnd}
                  isDragging={snapshot.isDraggingOver}
                  id={`${props.droppableId}-${index}`}
                  index={index}
                  key={`key-${props.droppableId}-${index}`}
                >
                  {props.renderRow(item, index)}
                </DndItem>
              ))}
              {provided.placeholder}
            </div>
          )}
        </StrictModeDroppable>
      </DragDropContext>
    </Box>
  );
}

export const useSortableList = <T extends unknown>(initialList: T[] = []) => {
  const [list, setList] = useState<T[]>(initialList);

  const onAddItem = (item: T) => {
    const newList = [...list];
    newList.push(item);
    setList(newList);
  };

  const onRemoveItem = (item: T) => {
    const newList = [...list];
    const index = newList.findIndex((listItem) => {
      return listItem === item;
    });

    if (index >= 0) {
      newList.splice(index, 1);
    }

    setList(newList);
  };

  const onSorted = (items: T[]) => {
    setList(items);
  };

  return {
    list,
    setList,
    onAddItem,
    onRemoveItem,
    onSorted,
  };
};
