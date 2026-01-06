import * as React from "react";
import { ReactNode } from "react";
import { FormattedMessage, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import { useRouter } from "next/router";
import Stack from "@mui/material/Stack";
import Grid from "@mui/material/Grid2";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import RemoveRedEyeIcon from "@mui/icons-material/RemoveRedEye";
import TextField from "@mui/material/TextField";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Typography from "@mui/material/Typography";
import FormHelperText from "@mui/material/FormHelperText";
import { useTheme } from "@mui/material/styles";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { Enrollment, EnrollmentState } from "@/services/api/models/Enrollment";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { PATH_ADMIN } from "@/utils/routes/path";
import { enrollmentStateMessages } from "@/translations/enrollments/enrollment-state";
import { enrollmentViewMessages } from "@/components/templates/enrollments/view/translations";

type Props = {
  enrollment: Enrollment;
};
export function EnrollmentView({ enrollment }: Props) {
  const intl = useIntl();
  const router = useRouter();
  const theme = useTheme();

  const getViewIcon = (url: string): ReactNode => {
    return (
      <Tooltip title={intl.formatMessage(commonTranslations.clickToView)}>
        <IconButton onClick={() => router.push(url)}>
          <RemoveRedEyeIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    );
  };

  return (
    <SimpleCard>
      <Box
        padding={4}
        sx={{
          ".MuiOutlinedInput-input.Mui-disabled, .MuiFormControlLabel-label.Mui-disabled":
            {
              textFillColor: theme.palette.text.primary,
            },
          ".MuiCheckbox-root.Mui-checked.Mui-disabled": {
            color: "primary.main",
          },
        }}
      >
        <Stack gap={2}>
          <Grid container spacing={2}>
            <Grid size={12}>
              <Typography variant="h6">
                <FormattedMessage
                  {...enrollmentViewMessages.mainSectionTitle}
                />
              </Typography>
            </Grid>
            <Grid size={12}>
              <TextField
                fullWidth={true}
                disabled={true}
                InputProps={{
                  endAdornment: getViewIcon(
                    PATH_ADMIN.courses_run.edit(enrollment.course_run.id),
                  ),
                }}
                label={intl.formatMessage(enrollmentViewMessages.courseRun)}
                value={enrollment.course_run.title}
              />
            </Grid>
            <Grid size={12}>
              <TextField
                fullWidth={true}
                disabled={true}
                label={intl.formatMessage(enrollmentViewMessages.user)}
                value={
                  enrollment.user.full_name !== ""
                    ? enrollment.user.full_name
                    : enrollment.user.username
                }
              />
            </Grid>
            <Grid size={12}>
              <TextField
                fullWidth={true}
                disabled={true}
                label={intl.formatMessage(enrollmentViewMessages.state)}
                helperText={
                  enrollment.state === EnrollmentState.FAILED && (
                    <Typography variant="subtitle2" color="error">
                      <FormattedMessage
                        {...enrollmentViewMessages.stateFailedMessage}
                      />
                    </Typography>
                  )
                }
                value={intl.formatMessage(
                  enrollmentStateMessages[enrollment.state],
                )}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControlLabel
                color="primary"
                control={
                  <Checkbox
                    disabled
                    checked={enrollment.was_created_by_order}
                  />
                }
                label={intl.formatMessage(
                  enrollmentViewMessages.wasCreatedForOrder,
                )}
              />
              <FormHelperText>
                <FormattedMessage
                  {...enrollmentViewMessages.wasCreatedForOrderHelperText}
                />
              </FormHelperText>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControlLabel
                color="primary"
                control={<Checkbox disabled checked={enrollment.is_active} />}
                label={intl.formatMessage(enrollmentViewMessages.isActive)}
              />
              <FormHelperText>
                <FormattedMessage
                  {...enrollmentViewMessages.isActiveHelperText}
                />
              </FormHelperText>
            </Grid>
          </Grid>
        </Stack>
      </Box>
    </SimpleCard>
  );
}
