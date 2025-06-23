import * as React from "react";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { OfferingDummy } from "@/services/api/models/Offerings";
import { OfferingSource } from "@/components/templates/offerings/offering/OfferingList";

type Props = {
  source: OfferingSource;
  offering: OfferingDummy;
};

export function OfferingDummyRow({ offering, source }: Props) {
  const getTitle = (): string => {
    return source === OfferingSource.COURSE
      ? offering.product!.title
      : offering.course!.title;
  };

  return (
    <DefaultRow
      loading={true}
      key={getTitle()}
      mainTitle={getTitle()}
      enableEdit={false}
      enableDelete={false}
      subTitle={offering.organizations.map((org) => org.title).join(",")}
    />
  );
}
