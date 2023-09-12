import * as React from "react";
import { useIntl } from "react-intl";
import {
  ProductTargetCourseRelation,
  ProductTargetCourseRelationOptionalId,
} from "@/services/api/models/ProductTargetCourseRelation";
import { productFormMessages } from "@/components/templates/products/form/translations";
import {
  DndDefaultRow,
  DndDefaultRowProps,
} from "@/components/presentational/dnd/DndDefaultRow";

type Props = Omit<DndDefaultRowProps, "mainTitle"> & {
  item: ProductTargetCourseRelation | ProductTargetCourseRelationOptionalId;
};
export function ProductFormTargetCourseRow({ item, ...props }: Props) {
  const intl = useIntl();
  return (
    <DndDefaultRow
      {...props}
      enableEdit={item.id !== undefined}
      enableDelete={item.id !== undefined}
      mainTitle={item.course?.title}
      subTitle={intl.formatMessage(
        productFormMessages.targetCourseRowSubTitle,
        { numPhotos: item.course_runs.length },
      )}
    />
  );
}
