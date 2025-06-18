import * as React from "react";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { OfferDummy } from "@/services/api/models/Offers";
import { OfferSource } from "@/components/templates/offers/offer/OfferList";

type Props = {
  source: OfferSource;
  offer: OfferDummy;
};

export function OfferDummyRow({ offer, source }: Props) {
  const getTitle = (): string => {
    return source === OfferSource.COURSE
      ? offer.product!.title
      : offer.course!.title;
  };

  return (
    <DefaultRow
      loading={true}
      key={getTitle()}
      mainTitle={getTitle()}
      enableEdit={false}
      enableDelete={false}
      subTitle={offer.organizations.map((org) => org.title).join(",")}
    />
  );
}
