import * as React from "react";
import RHFAutocomplete from "@/components/presentational/hook-form/RHFAutocomplete";
import { useAllLanguages } from "@/hooks/useAllLanguages/useAllLanguages";
import { Maybe } from "@/types/utils";

export interface JoanieLanguage {
  value: string;
  display_name: string;
}

interface Props {
  name: string;
  label: string;
  multiple?: boolean;
}

export function RHFSelectLanguage({ multiple = true, ...props }: Props) {
  const languages: JoanieLanguage[] = useAllLanguages();

  return (
    <RHFAutocomplete
      options={languages ?? []}
      multiple={multiple}
      getOptionLabel={(option: Maybe<JoanieLanguage>) => {
        return option?.display_name ?? "";
      }}
      isOptionEqualToValue={(option, value) => {
        return option.value === value.value;
      }}
      name={props.name}
      label={props.label}
    />
  );
}

export function useSelectLanguageUtils() {
  const languages: JoanieLanguage[] = useAllLanguages();
  const getObjectsFromValues = (toConvert: string[] = []): JoanieLanguage[] => {
    const newResult: JoanieLanguage[] = [];
    toConvert.forEach((lang) => {
      const search = languages.find((item) => {
        return item.value === lang;
      });

      if (search) {
        newResult.push(search);
      }
    });
    return newResult;
  };

  const getValuesFromObjects = (langs: JoanieLanguage[] = []): string[] => {
    return langs.map((lang) => {
      return lang.value;
    });
  };

  return {
    getObjectsFromValues,
    getValuesFromObjects,
  };
}
