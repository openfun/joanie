import * as React from "react";
import { ReactElement, useMemo } from "react";
import MoreVertOutlinedIcon from "@mui/icons-material/MoreVertOutlined";
import IconButton from "@mui/material/IconButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import MenuList from "@mui/material/MenuList";
import EditIcon from "@mui/icons-material/Edit";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import { useIntl } from "react-intl";
import {
  MenuPopover,
  useMenuPopover,
} from "@/components/presentational/menu-popover/MenuPopover";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { useModal } from "@/components/presentational/modal/useModal";
import { tableTranslations } from "@/components/presentational/table/translations";
import { commonTranslations } from "@/translations/common/commonTranslations";

export interface TableDefaultMenuItem {
  title: string;
  icon: ReactElement;
  onClick?: () => void;
}

interface Props {
  onDelete?: () => void;
  onEdit?: () => void;
  onUseAsTemplate?: () => void;
  entityName?: string;
  extendedOptions?: TableDefaultMenuItem[];
}

export function TableDefaultActions(props: Props) {
  const intl = useIntl();
  const menu = useMenuPopover();
  const deleteModal = useModal();

  const menuItems: TableDefaultMenuItem[] = useMemo(() => {
    const other = props.extendedOptions ?? [];
    let result = [];

    if (props.onEdit) {
      result.push({
        title: intl.formatMessage(commonTranslations.edit),
        icon: <EditIcon fontSize="small" />,
        onClick: props.onEdit,
      });
    }

    result = [...result, ...other];

    if (props.onUseAsTemplate) {
      result.push({
        title: intl.formatMessage(commonTranslations.useAsTemplate),
        icon: <ContentCopyOutlinedIcon fontSize="small" />,
        onClick: props.onUseAsTemplate,
      });
    }

    if (props.onDelete) {
      result.push({
        title: intl.formatMessage(commonTranslations.delete),
        icon: <DeleteOutlineOutlinedIcon color="error" fontSize="small" />,
        onClick: deleteModal.handleOpen,
      });
    }

    return result;
  }, [deleteModal.handleOpen, props.onEdit, props.onDelete]);

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
      {props.onDelete && (
        <AlertModal
          title={intl.formatMessage(tableTranslations.deleteModalTitle)}
          handleAccept={props.onDelete}
          message={intl.formatMessage(tableTranslations.deleteModalMessage, {
            entityName: props.entityName ? `(${props.entityName})` : "",
          })}
          open={deleteModal.open}
          handleClose={deleteModal.handleClose}
        />
      )}
    </>
  );
}
