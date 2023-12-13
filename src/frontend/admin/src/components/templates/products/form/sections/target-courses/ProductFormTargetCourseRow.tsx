import * as React from "react";
import { useIntl } from "react-intl";
import {
  ProductTargetCourseRelation,
  ProductTargetCourseRelationOptionalId,
} from "@/services/api/models/ProductTargetCourseRelation";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { DndDefaultRowProps } from "@/components/presentational/dnd/DndDefaultRow";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";

type Props = Omit<DndDefaultRowProps, "mainTitle"> & {
  item: ProductTargetCourseRelation | ProductTargetCourseRelationOptionalId;
};
export function ProductFormTargetCourseRow({ item, ...props }: Props) {
  const intl = useIntl();
  return (
    <DefaultRow
      {...props}
      testId={`product-target-course-${item.course.id}`}
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
