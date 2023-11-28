import * as React from "react";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { CourseRelationToProductDummy } from "@/services/api/models/Relations";

type Props = {
  relation: CourseRelationToProductDummy;
};

export function CourseProductRelationDummyRow({ relation }: Props) {
  return (
    <DefaultRow
      loading={true}
      key={relation.product.title}
      mainTitle={relation.product.title}
      enableEdit={false}
      enableDelete={false}
      subTitle={relation.organizations.map((org) => org.title).join(",")}
    />
  );
}
