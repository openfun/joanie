import * as React from "react";
import { useMemo, useState } from "react";
import { defineMessages, useIntl } from "react-intl";
import { Product, ProductType } from "@/services/api/models/Product";
import { Maybe } from "@/types/utils";
import { ProductFormMain } from "@/components/templates/products/form/sections/main/ProductFormMain";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { ProductFormTypeSection } from "@/components/templates/products/form/sections/ProductFormTypeSection";
import { ProductFormTargetCoursesSection } from "@/components/templates/products/form/sections/target-courses/ProductFormTargetCoursesSection";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { Wizard, WizardStep } from "@/components/presentational/wizard/Wizard";
import {
  TabsComponent,
  TabValue,
} from "@/components/presentational/tabs/TabsComponent";
import { ProductFormCourseProductRelations } from "@/components/templates/products/form/sections/course-product-relations/ProductFormCourseProductRelations";

const messages = defineMessages({
  syllabusTabTitle: {
    id: "components.templates.products.form.translations.syllabusTabTitle",
    defaultMessage: "Syllabus",
    description: "Title for the syllabus tab",
  },
  linkedCourseTabInfo: {
    id: "components.templates.products.form.translations.linkedCourseTabInfo",
    defaultMessage:
      "In this section, you have access to all courses to which this product is attached. Click on the course title to navigate to its detail.",
    description: "Text for the linked course info tab",
  },
  generalTabTitle: {
    id: "components.templates.products.form.translations.generalTabTitle",
    defaultMessage: "General",
    description: "Title for the linked course tab",
  },
  generalTabInfo: {
    id: "components.templates.products.form.translations.generalTabInfo",
    defaultMessage: "In this section you can create or modify a product.",
    description: "Text for the linked course info tab",
  },
});

type Props = {
  product?: Product;
  fromProduct?: Product;
  afterSubmit?: (product: Product) => void;
};

export function ProductForm({ product, fromProduct, afterSubmit }: Props) {
  const intl = useIntl();
  const [productType, setProductType] = useState<Maybe<ProductType>>(
    product?.type ?? fromProduct?.type,
  );

  const updateProductType = (newType: ProductType) => {
    setProductType(newType);
  };

  const formSteps: WizardStep[] = useMemo(() => {
    const result: WizardStep[] = [
      {
        label: intl.formatMessage(productFormMessages.mainSectionWizardTitle),
        component: (
          <ProductFormMain
            fromProduct={fromProduct}
            onResetType={() => setProductType(undefined)}
            productType={productType}
            product={product}
            afterSubmit={afterSubmit}
          />
        ),
      },
    ];

    if (productType === ProductType.CREDENTIAL && product) {
      result.push({
        label: intl.formatMessage(
          productFormMessages.targetCourseSectionWizardTitle,
        ),
        component: (
          <ProductFormTargetCoursesSection
            productId={product!.id}
            target_courses={product?.target_courses ?? []}
          />
        ),
      });
    }

    return result;
  }, [product, productType]);

  const tabs = useMemo(() => {
    const result: TabValue[] = [
      {
        label: intl.formatMessage(messages.generalTabTitle),
        tabInfo: intl.formatMessage(messages.generalTabInfo),
        component: (
          <SimpleCard>
            <Wizard steps={formSteps} />
          </SimpleCard>
        ),
      },
      {
        label: intl.formatMessage(messages.syllabusTabTitle),
        show: !!product,
        tabInfo: intl.formatMessage(messages.linkedCourseTabInfo),
        component: (
          <ProductFormCourseProductRelations
            relations={product?.course_relations ?? []}
          />
        ),
      },
    ];
    return result;
  }, [product, productType, formSteps]);

  if (!productType) {
    return (
      <ProductFormTypeSection
        active={productType}
        onSelectType={(type) => updateProductType(type)}
      />
    );
  }

  return <TabsComponent id="product-form-tabs" tabs={tabs} />;
}
