import * as React from "react";
import { useIntl } from "react-intl";
import {
  ProductTargetCourseRelation,
  ProductTargetCourseRelationOptionalId,
} from "@/services/api/models/ProductTargetCourseRelation";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { DndDefaultRowProps } from "@/components/presentational/dnd/DndDefaultRow";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";

type Props = Omit<DndDefaultRowProps, "mainTitle"> & {
  item: ProductTargetCourseRelation | ProductTargetCourseRelationOptionalId;
};

const isRelation = (
  item: ProductTargetCourseRelation | ProductTargetCourseRelationOptionalId,
): item is ProductTargetCourseRelation => {
  return "id" in item;
};

export function ProductFormTargetCourseRow({ item, ...props }: Props) {
  const intl = useIntl();
  const isDummy = !isRelation(item);

  return (
    <DefaultRow
      {...props}
      testId={`${isDummy ? "dummy" : "item"}-product-target-course-${
        item.course.id
      }`}
      enableEdit={item.id !== undefined}
      enableDelete={item.id !== undefined}
      mainTitle={
        <CustomLink href={PATH_ADMIN.courses.edit(item.course.id)}>
          {item.course.title}
        </CustomLink>
      }
      subTitle={intl.formatMessage(
        productFormMessages.targetCourseRowSubTitle,
        { numPhotos: item.course_runs.length },
      )}
    />
  );
}
