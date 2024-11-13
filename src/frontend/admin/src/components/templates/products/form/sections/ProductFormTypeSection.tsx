import * as React from "react";
import { useMemo } from "react";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";
import Chip from "@mui/material/Chip";
import { defineMessages, useIntl } from "react-intl";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { ProductType } from "@/services/api/models/Product";

const messages = defineMessages({
  microCredentialTitle: {
    id: "components.templates.products;form.sections.ProductFormTypeSection.microCredentialTitle",
    defaultMessage: "Microcredential",
    description: "Title for the credential product type",
  },
  microCredentialDescription: {
    id: "components.templates.products;form.sections.ProductFormTypeSection.microCredentialDescription",
    defaultMessage:
      "Our online microcredentials allow you to pursue further study in a specialised field. Created or accredited by world-leading universities, they are professional qualifications designed to help you master in-demand career skills and prepare for work in rapidly growing.",
    description: "Description for the credential product type",
  },
  certificateTitle: {
    id: "components.templates.products;form.sections.ProductFormTypeSection.certificateTitle",
    defaultMessage: "Certificate",
    description: "Description for the certificate product type",
  },
  certificateDescription: {
    id: "components.templates.products;form.sections.ProductFormTypeSection.certificateDescription",
    defaultMessage:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec auctor cursus tincidunt. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Morbi sit amet neque dolor. Mauris a ultrices nulla. Curabitur sit amet lectus eget arcu ultricies tristique eu et dui. Integer ut nibh tempor, pellentesque libero at, finibus risus.",
    description: "Description for the certificate product type",
  },
  certifyingBadgeLabel: {
    id: "components.templates.products;form.sections.ProductFormTypeSection.certifyingBadgeLabel",
    defaultMessage: "Certifying",
    description: "Label for the Certifying badge",
  },
});

type Props = {
  active?: ProductType;
  onSelectType: (type: ProductType) => void;
};

export function ProductFormTypeSection(props: Props) {
  const intl = useIntl();
  const theme = useTheme();
  const productTypes = useMemo(() => {
    return [
      {
        type: ProductType.CREDENTIAL,
        title: intl.formatMessage(messages.microCredentialTitle),
        description: intl.formatMessage(messages.microCredentialDescription),
        isCertificate: true,
      },
      {
        type: ProductType.CERTIFICATE,
        title: intl.formatMessage(messages.certificateTitle),
        description: intl.formatMessage(messages.certificateDescription),
        isCertificate: true,
      },
    ];
  }, []);

  return (
    <Stack spacing={4} padding={3}>
      <Typography variant="h6">Product type: {props.active}</Typography>
      <Stack
        justifyContent="center"
        alignItems="stretch"
        direction={{ xs: "column", sm: "column", md: "row" }}
        spacing={6}
      >
        {productTypes.map((type) => {
          return (
            <Box
              key={type.type}
              sx={{
                display: "flex",
                padding: props.active === type.type ? "2px" : "1px",
                borderRadius: "6px",
                boxShadow: "0px 2px 6px 0px rgba(0, 0, 0, 0.25)",
                background:
                  "linear-gradient(96.79deg, #6AB8FF 0%, #6AB8FF 50%, #F0F8FF 100%)",
                backgroundSize: "200% 100%",
                backgroundPosition:
                  props.active === type.type ? "0% 0" : "100% 0",
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
                  background:
                    "linear-gradient(96.79deg, #6AB8FF 0%, #152327 100%)",
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
                onClick={() => props.onSelectType(type.type)}
                padding={4}
                sx={{
                  borderRadius: "6px",
                  cursor: "pointer",
                  background: theme.palette.background.default,
                }}
              >
                <Stack spacing={2}>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="subtitle2">{type.title}</Typography>
                    <Chip
                      color="info"
                      size="small"
                      sx={{
                        backgroundColor: "#f1f8ff",
                        color: "info.main",
                        borderRadius: "6px",
                        ...theme.applyStyles("dark", {
                          backgroundColor: "#111822",
                        }),
                      }}
                      label={intl.formatMessage(messages.certifyingBadgeLabel)}
                    />
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      {type.description}
                    </Typography>
                    <Box
                      className="go-button"
                      ml={3}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "transform 200ms ease",
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
                </Stack>
              </Box>
            </Box>
          );
        })}
      </Stack>
    </Stack>
  );
}
