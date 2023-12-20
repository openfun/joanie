import * as React from "react";
import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import { useIntl } from "react-intl";
import { Product, ProductType } from "@/services/api/models/Product";
import { Maybe } from "@/types/utils";
import { ProductFormMain } from "@/components/templates/products/form/sections/main/ProductFormMain";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { ProductFormTypeSection } from "@/components/templates/products/form/sections/ProductFormTypeSection";
import { ProductFormTargetCoursesSection } from "@/components/templates/products/form/sections/target-courses/ProductFormTargetCoursesSection";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { Wizard, WizardStep } from "@/components/presentational/wizard/Wizard";
import { ProductFormCourseProductRelations } from "@/components/templates/products/form/sections/course-product-relations/ProductFormCourseProductRelations";

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

  if (!productType) {
    return (
      <ProductFormTypeSection
        active={productType}
        onSelectType={(type) => updateProductType(type)}
      />
    );
  }

  return (
    <>
      <SimpleCard>
        <Box padding={4}>
          <Wizard steps={formSteps} />
        </Box>
      </SimpleCard>
      {product && (
        <Box mt={6}>
          <ProductFormCourseProductRelations
            relations={product.course_relations}
          />
        </Box>
      )}
    </>
  );
}
