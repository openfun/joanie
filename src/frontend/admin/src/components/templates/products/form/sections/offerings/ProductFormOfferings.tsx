import * as React from "react";
import { Product } from "@/services/api/models/Product";
import { OfferingList } from "@/components/templates/offerings/offering/OfferingList";
import { useProducts } from "@/hooks/useProducts/useProducts";

type Props = {
  product: Product;
};
export function ProductFormOfferings({ product }: Props) {
  const productRepository = useProducts({}, { enabled: false });

  return (
    <OfferingList
      productId={product.id}
      offerings={product.offerings ?? []}
      invalidate={productRepository.methods.invalidate}
    />
  );
}
