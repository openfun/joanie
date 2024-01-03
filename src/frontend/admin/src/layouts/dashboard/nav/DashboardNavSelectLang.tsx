import * as React from "react";
import PublicIcon from "@mui/icons-material/Public";
import { BasicSelect } from "@/components/presentational/inputs/select/BasicSelect";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";
import { StyledItem } from "@/layouts/dashboard/nav/item/StyledItem";
import { useLocale } from "@/contexts/i18n/TranslationsProvider/TranslationContext";

export function DashboardNavSelectLang() {
  const locale = useLocale();
  return (
    <StyledItem sx={{ p: 2 }}>
      <PublicIcon sx={{ mr: 2 }} />
      <BasicSelect
        data-testid="select-language"
        sx={{
          boxShadow: "none",
          ".MuiOutlinedInput-notchedOutline": { border: 0 },
        }}
        size="small"
        value={locale.currentLocale}
        onSelect={(newValue) => {
          locale.setCurrentLocale(newValue);
        }}
        label=""
        options={[
          { value: LocalesEnum.ENGLISH, label: "English" },
          { value: LocalesEnum.FRENCH, label: "Français" },
        ]}
      />
    </StyledItem>
  );
}
