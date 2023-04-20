import * as React from "react";
import { ReactElement, useMemo } from "react";
import MoreVertOutlinedIcon from "@mui/icons-material/MoreVertOutlined";
import {
  IconButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  MenuList,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";
import { useIntl } from "react-intl";
import {
  MenuPopover,
  useMenuPopover,
} from "@/components/presentational/menu-popover/MenuPopover";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { useModal } from "@/components/presentational/modal/useModal";
import { tableTranslations } from "@/components/presentational/table/translations";

interface TableDefaultMenuItem {
  title: string;
  icon: ReactElement;
  onClick?: () => void;
}

interface Props {
  onDelete: () => void;
  onEdit: () => void;
  entityName?: string;
}

export function TableDefaultActions(props: Props) {
  const intl = useIntl();
  const menu = useMenuPopover();
  const deleteModal = useModal();

  const menuItems: TableDefaultMenuItem[] = useMemo(() => {
    return [
      {
        title: "Edit",
        icon: <EditIcon fontSize="small" />,
        onClick: props.onEdit,
      },
      {
        title: "Delete",
        icon: <DeleteOutlineOutlinedIcon color="error" fontSize="small" />,
        onClick: deleteModal.handleOpen,
      },
    ];
  }, []);

  return (
    <>
      <IconButton onClick={menu.open}>
        <MoreVertOutlinedIcon />
      </IconButton>
      <MenuPopover open={menu.anchor} onClose={menu.close} arrow="right-top">
        <MenuList>
          {menuItems.map((item) => {
            return (
              <MenuItem
                onClick={() => {
                  menu.close();
                  item.onClick?.();
                }}
                key={item.title}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText>{item.title}</ListItemText>
              </MenuItem>
            );
          })}
        </MenuList>
      </MenuPopover>
      <AlertModal
        title={intl.formatMessage(tableTranslations.deleteModalTitle)}
        handleAccept={props.onDelete}
        message={intl.formatMessage(tableTranslations.deleteModalMessage, {
          entityName: props.entityName ? `(${props.entityName})` : "",
        })}
        open={deleteModal.open}
        handleClose={deleteModal.handleClose}
      />
    </>
  );
}
