import * as React from "react";
import { useState } from "react";
import Grid from "@mui/material/Grid2";
import Typography from "@mui/material/Typography";
import { useIntl } from "react-intl";
import { useFormContext } from "react-hook-form";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { productFormMessages } from "@/components/templates/products/form/translations";
import { MarkdownComponent } from "@/components/presentational/inputs/markdown/MardownComponent";

export function ProductFormInstructions() {
  const intl = useIntl();
  const [showMarkdownEdit, setShowMarkdownEdit] = useState(false);
  const { watch, setValue } = useFormContext();
  const instructionValue = watch("instructions");

  return (
    <Grid container spacing={2}>
      <Grid size={12}>
        <Accordion
          expanded={showMarkdownEdit}
          sx={{ boxShadow: "none" }}
          onChange={() => setShowMarkdownEdit(!showMarkdownEdit)}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            sx={{ px: 0, display: "flex", alignItems: "center" }}
            aria-controls="panel1a-content"
            id="panel1a-header"
          >
            <Typography variant="subtitle2">
              {intl.formatMessage(productFormMessages.instructionsTitle)}
            </Typography>
            {!showMarkdownEdit && (
              <Typography variant="caption" alignSelf="center">
                &nbsp;
                {intl.formatMessage(productFormMessages.instructionsTitleHelp)}
              </Typography>
            )}
          </AccordionSummary>
          <AccordionDetails>
            <MarkdownComponent
              value={instructionValue ?? ""}
              onChange={(markdown) => {
                setValue("instructions", markdown ?? "", {
                  shouldDirty: true,
                });
              }}
            />
          </AccordionDetails>
        </Accordion>
      </Grid>
    </Grid>
  );
}
