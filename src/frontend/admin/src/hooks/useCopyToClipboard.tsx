import { useIntl } from "react-intl";
import { useSnackbar } from "notistack";
import { commonTranslations } from "@/translations/common/commonTranslations";

export const useCopyToClipboard = () => {
  const intl = useIntl();
  const snackbar = useSnackbar();
  return (str: string) => {
    navigator.clipboard.writeText(str).then(() => {
      snackbar.enqueueSnackbar(
        intl.formatMessage(commonTranslations.successCopy),
        {
          variant: "success",
          preventDuplicate: true,
        },
      );
    });
  };
};
