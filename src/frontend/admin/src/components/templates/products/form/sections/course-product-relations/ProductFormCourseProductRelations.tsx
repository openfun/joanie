import * as React from "react";
import { Product } from "@/services/api/models/Product";
import { CourseProductRelationList } from "@/components/templates/relations/course-product-relation/CourseProductRelationList";
import { useProducts } from "@/hooks/useProducts/useProducts";

type Props = {
  product: Product;
};
export function ProductFormCourseProductRelations({ product }: Props) {
  const productRepository = useProducts({}, { enabled: false });

  return (
    <CourseProductRelationList
      productId={product.id}
      relations={product.course_relations ?? []}
      invalidate={productRepository.methods.invalidate}
    />
  );
}
