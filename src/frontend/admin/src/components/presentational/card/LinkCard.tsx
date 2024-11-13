import { ReactNode } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { useTheme } from "@mui/material/styles";
import { CustomLink } from "@/components/presentational/link/CustomLink";

type Props = {
  icon?: ReactNode;
  title: string;
  href: string;
  description: string;
  badgeLabel?: string;
};
export function LinkCard(props: Props) {
  const theme = useTheme();
  return (
    <CustomLink href={props.href} underline="none">
      <Box
        sx={{
          position: "relative",
          display: "flex",
          padding: "1px",
          borderRadius: "6px",
          height: "100%",
          boxShadow: "0px 2px 6px 0px rgba(0, 0, 0, 0.25)",
          background:
            "linear-gradient(96.79deg, #6AB8FF 0%, #6AB8FF 50%, #F0F8FF 100%)",
          backgroundSize: "200% 100%",
          backgroundPosition: "100% 0",
          transition:
            "background-position 400ms ease-out, box-shadow 400ms ease-out",

          "&:hover": {
            backgroundPosition: "0% 0",
            boxShadow: "0px 0px 2px 0px rgba(0, 0, 0, 0.25)",

            ".go-button": {
              transform: "translate(20%, 0%)",
            },
          },

          ...theme.applyStyles("dark", {
            background: "linear-gradient(96.79deg, #6AB8FF 0%, #152327 100%)",
            boxShadow: "0px 2px 6px 0px rgba(125, 125, 200, 0.15)",

            "&:hover": {
              backgroundPosition: "0% 0",
              boxShadow: "0px 0px 2px 0px rgba(125, 125, 200, 0.1)",

              ".go-button": {
                transform: "translate(20%, 0%)",
              },
            },
          }),
        }}
      >
        <Box
          padding={4}
          sx={{
            borderRadius: "6px",
            cursor: "pointer",
            width: "100%",
            background: theme.palette.background.default,
          }}
        >
          <Stack spacing={2}>
            <Box
              display="flex"
              justifyContent="space-between"
              sx={{
                flexDirection: {
                  xs: "column",
                  lg: "row",
                },
              }}
            >
              <Box display="flex" alignItems="center">
                <Box sx={{ alignSelf: { sm: "flex-start" } }}>{props.icon}</Box>
                <Typography sx={{ ml: 1 }} variant="subtitle2">
                  {props.title}
                </Typography>
              </Box>
              {props.badgeLabel && (
                <Chip
                  color="info"
                  size="small"
                  sx={{
                    mt: { xs: 1.3 },
                    alignSelf: "flex-start ",
                    backgroundColor: "#f1f8ff",
                    color: "info.main",
                    borderRadius: "6px",
                    ...theme.applyStyles("dark", {
                      backgroundColor: "#111822",
                    }),
                  }}
                  label={props.badgeLabel}
                />
              )}
            </Box>
            <Box display="flex" pr={6} justifyContent="space-between">
              <Typography variant="body2" color="text.secondary">
                {props.description}
              </Typography>
            </Box>
          </Stack>
        </Box>
        <Box
          className="go-button"
          ml={3}
          sx={{
            position: "absolute",
            bottom: "20px",
            right: "20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "transform 400ms ease-out",
            backgroundColor: "info.light",
            color: "background.default",
            alignSelf: "end",
            borderRadius: "50%",
            width: "30px",
            minWidth: "30px",
            height: "30px",
          }}
        >
          <ArrowForwardIcon fontSize="small" color="inherit" />
        </Box>
      </Box>
    </CustomLink>
  );
}
