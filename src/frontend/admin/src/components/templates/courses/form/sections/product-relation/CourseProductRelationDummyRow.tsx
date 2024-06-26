import * as React from "react";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { CourseProductRelationDummy } from "@/services/api/models/Relations";
import { CourseProductRelationSource } from "@/components/templates/relations/course-product-relation/CourseProductRelationList";

type Props = {
  source: CourseProductRelationSource;
  relation: CourseProductRelationDummy;
};

export function CourseProductRelationDummyRow({ relation, source }: Props) {
  const getTitle = (): string => {
    return source === CourseProductRelationSource.COURSE
      ? relation.product!.title
      : relation.course!.title;
  };

  return (
    <DefaultRow
      loading={true}
      key={getTitle()}
      mainTitle={getTitle()}
      enableEdit={false}
      enableDelete={false}
      subTitle={relation.organizations.map((org) => org.title).join(",")}
    />
  );
}
