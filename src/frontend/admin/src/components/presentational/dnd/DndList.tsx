import * as React from "react";
import { useEffect, useState } from "react";
import { DragDropContext, DropResult } from "react-beautiful-dnd";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import { defineMessages, useIntl } from "react-intl";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import { faker } from "@faker-js/faker";
import { StrictModeDroppable } from "@/components/presentational/dnd/StrictModeDroppable";
import { DndItem } from "@/components/presentational/dnd/DndItem";
import { commonTranslations } from "@/translations/common/commonTranslations";

const messages = defineMessages({
  emptyList: {
    id: "components.presentational.dnd.DndList.emptyList",
    description: "Text when the drag n drop list is empty",
    defaultMessage: "No line to display, click add to add one",
  },
});

export interface Row {
  id?: string;
}

export interface RowPropsExtended<T> {
  item: T;
}

export interface DndListProps<
  TRowProps extends Row,
  TCreatingRowProps extends Row,
> {
  droppableId: string;
  disableDnd?: boolean;
  rows: TRowProps[];
  renderRow: (item: TRowProps, index: number) => React.ReactNode;
  creatingRows?: TCreatingRowProps[];
  renderCreatingRow?: (
    item: TCreatingRowProps,
    index: number,
  ) => React.ReactNode;
  onSorted: (items: TRowProps[]) => void;
  addButtonLabel?: string;
  addButtonClick?: () => void;
  emptyLabel?: string;
  headerActions?: React.ReactNode;
}

export function DndList<TRowProps extends Row, TCreatingRowProps extends Row>({
  ...props
}: DndListProps<TRowProps, TCreatingRowProps>) {
  const intl = useIntl();
  const [dummyRows, setDummyRows] = useState<TCreatingRowProps[]>([]);
  const onDragEnd = (result: DropResult) => {
    const { destination, source } = result;
    const newItems = [...props.rows];
    if (destination && source) {
      const old = newItems.splice(source.index, 1);
      newItems.splice(destination.index, 0, ...old);
    }

    props.onSorted(newItems);
  };

  useEffect(() => {
    const result: TCreatingRowProps[] = [];
    props.creatingRows?.forEach((item) => {
      const clone = { ...item };
      if (!clone.id) {
        clone.id = faker.string.uuid();
      }
      result.push(clone);
    });

    setDummyRows(result);
  }, [props.creatingRows]);

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
                  index={index}
                  id={`row-${props.droppableId}-${item.id}`}
                  key={`key-${props.droppableId}-${item.id}`}
                >
                  {props.renderRow(item, index)}
                </DndItem>
              ))}
              {dummyRows.map((item, index) => (
                <DndItem
                  isDragging={false}
                  isDisabled={true}
                  isLoading={true}
                  id={`row-${index}`}
                  index={props.rows.length + index}
                  key={`creating-key-${item.id}`}
                >
                  {props.renderCreatingRow?.(item, index)}
                </DndItem>
              ))}
              {provided.placeholder}
              <Stack spacing={2}>
                {props.rows.length === 0 && (
                  <Box
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                  >
                    <Typography width="100%" align="center" variant="caption">
                      {props.emptyLabel ??
                        intl.formatMessage(messages.emptyList)}
                    </Typography>
                  </Box>
                )}
                {props.addButtonClick && (
                  <Button fullWidth onClick={props.addButtonClick}>
                    {props.addButtonLabel ??
                      intl.formatMessage(commonTranslations.add)}
                  </Button>
                )}
              </Stack>
            </div>
          )}
        </StrictModeDroppable>
      </DragDropContext>
    </Box>
  );
}
