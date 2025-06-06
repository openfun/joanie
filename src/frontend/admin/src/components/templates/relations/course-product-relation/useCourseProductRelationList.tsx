import { useMemo, useState } from "react";
import { faker } from "@faker-js/faker";
import { useModal } from "@/components/presentational/modal/useModal";
import { useList } from "@/hooks/useList/useList";
import {
  CourseProductRelation,
  CourseProductRelationDummy,
  DTOCourseProductRelation,
} from "@/services/api/models/Relations";
import { CourseProductRelationFormValues } from "@/components/templates/courses/form/product-relation/CourseProductRelationForm";
import { useCourseProductRelations } from "@/hooks/useCourseProductRelation/useCourseProductRelation";

type EditRelationState = {
  relation: CourseProductRelation;
  index: number;
};

enum Mode {
  EDIT = "edit",
  ADD = "add",
}

type Props = {
  courseId?: string;
  productId?: string;
  relations: CourseProductRelation[];
  invalidate: () => void;
};

export const useCourseProductRelationList = ({
  relations = [],
  invalidate,
}: Props) => {
  const relationToProductModal = useModal();
  const [relationToEdit, setRelationToEdit] = useState<EditRelationState>();
  const modalForm = useModal();
  const resourceQuery = useCourseProductRelations({}, { enabled: false });

  const relationList = useList<CourseProductRelation>(relations);
  const dummyRelationList = useList<CourseProductRelationDummy>([]);

  const mode: Mode = useMemo(() => {
    return relationToEdit?.relation !== undefined ? Mode.EDIT : Mode.ADD;
  }, [relationToEdit?.relation]);

  const handleCreate = (
    payload: DTOCourseProductRelation,
    formValues: CourseProductRelationFormValues,
  ) => {
    const dummy: CourseProductRelationDummy = {
      ...formValues,
      can_edit: false,
      offer_rules: [],
      dummyId: faker.string.uuid(),
    };

    modalForm.handleClose();
    dummyRelationList.clear();
    dummyRelationList.push(dummy);
    resourceQuery.methods.create(payload, {
      onSuccess: (data) => {
        relationList.insertAt(0, data);
      },
      onSettled: () => {
        dummyRelationList.clear();
      },
    });
  };

  const afterEdit = (
    editMode: "error" | "success",
    data?: CourseProductRelation,
  ) => {
    if (!relationToEdit) {
      return;
    }

    if (editMode === "error") {
      relationList.updateAt(relationToEdit.index, relationToEdit.relation);
    }

    if (editMode === "success" && data) {
      relationList.updateAt(relationToEdit.index, data);
      setRelationToEdit(undefined);
      resourceQuery.methods.invalidate();
      invalidate();
    }

    dummyRelationList.clear();
  };

  const handleEdit = (
    relationId: string,
    payload: DTOCourseProductRelation,
    formValues: CourseProductRelationFormValues,
  ) => {
    const relation = relationToEdit?.relation!;
    const dummy: CourseProductRelation = {
      ...relation,
      ...formValues,
      course: formValues.course ?? relation.course,
      product: formValues.product ?? relation.product,
    };

    relationList.updateAt(relationToEdit!.index, dummy);
    resourceQuery.methods.update(
      { id: relationId, ...payload },
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
    if (!relationToEdit) {
      return;
    }

    const relationId = relationToEdit.relation.id;

    relationToProductModal.handleClose();
    relationList.removeAt(relationToEdit?.index);
    resourceQuery.methods.delete(relationId, {
      onSuccess: () => {
        setRelationToEdit(undefined);
        resourceQuery.methods.invalidate();
        invalidate();
      },
      onError: () => {
        relationList.insertAt(relationToEdit?.index, relationToEdit.relation);
      },
    });
  };

  const onSubmit = async (
    payload: DTOCourseProductRelation,
    formValues: CourseProductRelationFormValues,
  ): Promise<void> => {
    if (mode === Mode.ADD) {
      handleCreate(payload, formValues);
    } else {
      handleEdit(relationToEdit!.relation!.id, payload, formValues);
    }
  };

  return {
    relationList,
    setRelationToEdit,
    relationToEdit,
    dummyRelationList,
    handleCreate,
    handleEdit,
    handleDelete,
    modalForm,
    onSubmit,
  };
};
