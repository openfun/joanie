import { useMemo, useState } from "react";
import { faker } from "@faker-js/faker";
import { useModal } from "@/components/presentational/modal/useModal";
import { useList } from "@/hooks/useList/useList";
import { Offer, OfferDummy, DTOOffer } from "@/services/api/models/Offers";
import { OfferFormValues } from "@/components/templates/courses/form/offer/OfferForm";
import { useOffers } from "@/hooks/useOffer/useOffer";

type EditOfferState = {
  offer: Offer;
  index: number;
};

enum Mode {
  EDIT = "edit",
  ADD = "add",
}

type Props = {
  courseId?: string;
  productId?: string;
  offers: Offer[];
  invalidate: () => void;
};

export const useOfferList = ({ offers = [], invalidate }: Props) => {
  const offerModal = useModal();
  const [offerToEdit, setOfferToEdit] = useState<EditOfferState>();
  const modalForm = useModal();
  const resourceQuery = useOffers({}, { enabled: false });

  const offerList = useList<Offer>(offers);
  const dummyOfferList = useList<OfferDummy>([]);

  const mode: Mode = useMemo(() => {
    return offerToEdit?.offer !== undefined ? Mode.EDIT : Mode.ADD;
  }, [offerToEdit?.offer]);

  const handleCreate = (payload: DTOOffer, formValues: OfferFormValues) => {
    const dummy: OfferDummy = {
      ...formValues,
      can_edit: false,
      offer_rules: [],
      dummyId: faker.string.uuid(),
    };

    modalForm.handleClose();
    dummyOfferList.clear();
    dummyOfferList.push(dummy);
    resourceQuery.methods.create(payload, {
      onSuccess: (data) => {
        offerList.insertAt(0, data);
      },
      onSettled: () => {
        dummyOfferList.clear();
      },
    });
  };

  const afterEdit = (editMode: "error" | "success", data?: Offer) => {
    if (!offerToEdit) {
      return;
    }

    if (editMode === "error") {
      offerList.updateAt(offerToEdit.index, offerToEdit.offer);
    }

    if (editMode === "success" && data) {
      offerList.updateAt(offerToEdit.index, data);
      setOfferToEdit(undefined);
      resourceQuery.methods.invalidate();
      invalidate();
    }

    dummyOfferList.clear();
  };

  const handleEdit = (
    offerId: string,
    payload: DTOOffer,
    formValues: OfferFormValues,
  ) => {
    const offer = offerToEdit?.offer!;
    const dummy: Offer = {
      ...offer,
      ...formValues,
      course: formValues.course ?? offer.course,
      product: formValues.product ?? offer.product,
    };

    offerList.updateAt(offerToEdit!.index, dummy);
    resourceQuery.methods.update(
      { id: offerId, ...payload },
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
    if (!offerToEdit) {
      return;
    }

    const offerId = offerToEdit.offer.id;

    offerModal.handleClose();
    offerList.removeAt(offerToEdit?.index);
    resourceQuery.methods.delete(offerId, {
      onSuccess: () => {
        setOfferToEdit(undefined);
        resourceQuery.methods.invalidate();
        invalidate();
      },
      onError: () => {
        offerList.insertAt(offerToEdit?.index, offerToEdit.offer);
      },
    });
  };

  const onSubmit = async (
    payload: DTOOffer,
    formValues: OfferFormValues,
  ): Promise<void> => {
    if (mode === Mode.ADD) {
      handleCreate(payload, formValues);
    } else {
      handleEdit(offerToEdit!.offer!.id, payload, formValues);
    }
  };

  return {
    offerList,
    setOfferToEdit,
    offerToEdit,
    dummyOfferList,
    handleCreate,
    handleEdit,
    handleDelete,
    modalForm,
    onSubmit,
  };
};
