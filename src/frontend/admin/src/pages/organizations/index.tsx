import { Button } from "@mui/material";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";

export default function Organizations() {
  return (
    <DashboardLayoutPage
      headerActions={
        <Button size="small" variant="contained">
          Add
        </Button>
      }
    >
      Organization Page
    </DashboardLayoutPage>
  );
}
