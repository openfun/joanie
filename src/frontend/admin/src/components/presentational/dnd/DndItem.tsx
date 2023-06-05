import * as React from "react";
import { PropsWithChildren } from "react";
import * as ReactDOM from "react-dom";
import { Draggable } from "react-beautiful-dnd";
import Box from "@mui/material/Box";
import DragIndicatorRoundedIcon from "@mui/icons-material/DragIndicatorRounded";
import { StyledDndItemContainer } from "@/components/presentational/dnd/StyledDndItemContainer";

interface Props {
  id: string;
  index: number;
  isDragging: boolean;
  isDisabled?: boolean;
}

export function DndItem({
  isDisabled = false,
  ...props
}: PropsWithChildren<Props>) {
  return (
    <Draggable
      isDragDisabled={isDisabled}
      draggableId={props.id}
      index={props.index}
    >
      {(provided, snapshot) => {
        const result = (
          <StyledDndItemContainer
            {...provided.draggableProps}
            ref={provided.innerRef}
            showHandle={
              (props.isDragging && !snapshot.isDragging) || isDisabled
            }
          >
            {!isDisabled && (
              <Box
                {...provided.dragHandleProps}
                className="dnd-handle"
                sx={{ opacity: 0, mr: 0.5 }}
              >
                <DragIndicatorRoundedIcon fontSize="small" color="disabled" />
              </Box>
            )}
            <Box sx={{ flexGrow: 1 }}>{props.children}</Box>
          </StyledDndItemContainer>
        );

        if (snapshot.isDragging) {
          return ReactDOM.createPortal(result, document.body);
        }
        return result;
      }}
    </Draggable>
  );
}
