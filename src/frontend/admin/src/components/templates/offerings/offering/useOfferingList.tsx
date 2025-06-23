import { useMemo, useState } from "react";
import { faker } from "@faker-js/faker";
import { useModal } from "@/components/presentational/modal/useModal";
import { useList } from "@/hooks/useList/useList";
import {
  Offering,
  OfferingDummy,
  DTOOffering,
} from "@/services/api/models/Offerings";
import { OfferingFormValues } from "@/components/templates/courses/form/offering/OfferingForm";
import { useOfferings } from "@/hooks/useOffering/useOffering";

type EditOfferingState = {
  offering: Offering;
  index: number;
};

enum Mode {
  EDIT = "edit",
  ADD = "add",
}

type Props = {
  courseId?: string;
  productId?: string;
  offerings: Offering[];
  invalidate: () => void;
};

export const useOfferingList = ({ offerings = [], invalidate }: Props) => {
  const offeringModal = useModal();
  const [offeringToEdit, setOfferingToEdit] = useState<EditOfferingState>();
  const modalForm = useModal();
  const resourceQuery = useOfferings({}, { enabled: false });

  const offeringList = useList<Offering>(offerings);
  const dummyOfferingList = useList<OfferingDummy>([]);

  const mode: Mode = useMemo(() => {
    return offeringToEdit?.offering !== undefined ? Mode.EDIT : Mode.ADD;
  }, [offeringToEdit?.offering]);

  const handleCreate = (
    payload: DTOOffering,
    formValues: OfferingFormValues,
  ) => {
    const dummy: OfferingDummy = {
      ...formValues,
      can_edit: false,
      offering_rules: [],
      dummyId: faker.string.uuid(),
    };

    modalForm.handleClose();
    dummyOfferingList.clear();
    dummyOfferingList.push(dummy);
    resourceQuery.methods.create(payload, {
      onSuccess: (data) => {
        offeringList.insertAt(0, data);
      },
      onSettled: () => {
        dummyOfferingList.clear();
      },
    });
  };

  const afterEdit = (editMode: "error" | "success", data?: Offering) => {
    if (!offeringToEdit) {
      return;
    }

    if (editMode === "error") {
      offeringList.updateAt(offeringToEdit.index, offeringToEdit.offering);
    }

    if (editMode === "success" && data) {
      offeringList.updateAt(offeringToEdit.index, data);
      setOfferingToEdit(undefined);
      resourceQuery.methods.invalidate();
      invalidate();
    }

    dummyOfferingList.clear();
  };

  const handleEdit = (
    offeringId: string,
    payload: DTOOffering,
    formValues: OfferingFormValues,
  ) => {
    const offering = offeringToEdit?.offering!;
    const dummy: Offering = {
      ...offering,
      ...formValues,
      course: formValues.course ?? offering.course,
      product: formValues.product ?? offering.product,
    };

    offeringList.updateAt(offeringToEdit!.index, dummy);
    resourceQuery.methods.update(
      { id: offeringId, ...payload },
      {
        onSuccess: (data) => {
          afterEdit("success", data);
        },
        onError: () => {
          afterEdit("error");
        },
      },
    );
  };

  const handleDelete = () => {
    if (!offeringToEdit) {
      return;
    }

    const offeringId = offeringToEdit.offering.id;

    offeringModal.handleClose();
    offeringList.removeAt(offeringToEdit?.index);
    resourceQuery.methods.delete(offeringId, {
      onSuccess: () => {
        setOfferingToEdit(undefined);
        resourceQuery.methods.invalidate();
        invalidate();
      },
      onError: () => {
        offeringList.insertAt(offeringToEdit?.index, offeringToEdit.offering);
      },
    });
  };

  const onSubmit = async (
    payload: DTOOffering,
    formValues: OfferingFormValues,
  ): Promise<void> => {
    if (mode === Mode.ADD) {
      handleCreate(payload, formValues);
    } else {
      handleEdit(offeringToEdit!.offering!.id, payload, formValues);
    }
  };

  return {
    offeringList,
    setOfferingToEdit,
    offeringToEdit,
    dummyOfferingList,
    handleCreate,
    handleEdit,
    handleDelete,
    modalForm,
    onSubmit,
  };
};
