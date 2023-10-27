import { ReactNode } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { CustomLink } from "@/components/presentational/link/CustomLink";

type Props = {
  icon?: ReactNode;
  title: string;
  href: string;
  description: string;
  badgeLabel?: string;
};
export function LinkCard(props: Props) {
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
          background: "linear-gradient(96.79deg, #6AB8FF 0%, #F0F8FF 100%)",
          transition: "background, box-shadow 200ms linear",

          "&:hover": {
            background: "#6AB8FF",
            boxShadow: "0px 0px 2px 0px rgba(0, 0, 0, 0.25)",

            ".go-button": {
              transform: "translate(20%, 0%)",
            },
          },
        }}
      >
        <Box
          padding={4}
          sx={{
            borderRadius: "6px",
            cursor: "pointer",
            width: "100%",
            background: "white",
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
            transition: "transform 200ms ease",
            backgroundColor: "info.light",
            color: "white",
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
