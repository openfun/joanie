import { Optional } from "@/types/utils";

export type QuoteDefinition = {
  id: string;
  title: string;
  description: string;
  body: string;
  language: string;
  name: QuoteDefinitionTemplate;
};

export type QuoteDefinitionFormValues = Omit<QuoteDefinition, "id" | "name"> & {
  name: QuoteDefinitionTemplate | "";
};

export type DTOQuoteDefinition = Optional<QuoteDefinition, "id">;

export enum QuoteDefinitionTemplate {
  DEFAULT = "quote_default",
}
