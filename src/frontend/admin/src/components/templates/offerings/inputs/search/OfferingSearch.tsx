import * as React from "react";
import { useState } from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Maybe } from "@/types/utils";
import { Offering } from "@/services/api/models/Offerings";
import { useOfferings } from "@/hooks/useOffering/useOffering";
import { OfferingRepository } from "@/services/repositories/offering/OfferingRepository";

const messages = defineMessages({
  searchLabel: {
    id: "components.templates.offerings.inputs.search.OfferingSearch.searchLabel",
    defaultMessage: "Offering search",
    description: "Label for the OfferingSearch component",
  },
});

const getOfferingLabel = (offering: Maybe<Offering>): string => {
  if (!offering) return "";
  return `${offering.product.title} — ${offering.course.title}`;
};

export function OfferingSearch(props: RHFAutocompleteSearchProps<Offering>) {
  const intl = useIntl();
  const [query, setQuery] = useState("");
  const offerings = useOfferings({ query });

  return (
    <RHFSearch
      {...props}
      findFilterValue={async (values) => {
        const request = await OfferingRepository.getAll({ ids: values });
        return request.results;
      }}
      items={offerings.items}
      label={props.label ?? intl.formatMessage(messages.searchLabel)}
      loading={offerings.states.fetching}
      onFilter={setQuery}
      getOptionLabel={getOfferingLabel}
      isOptionEqualToValue={(option, value) => option.id === value.id}
    />
  );
}
