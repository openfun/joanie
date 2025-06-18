import * as React from "react";
import { Product } from "@/services/api/models/Product";
import { OfferList } from "@/components/templates/offers/offer/OfferList";
import { useProducts } from "@/hooks/useProducts/useProducts";

type Props = {
  product: Product;
};
export function ProductFormOffers({ product }: Props) {
  const productRepository = useProducts({}, { enabled: false });

  return (
    <OfferList
      productId={product.id}
      offers={product.offers ?? []}
      invalidate={productRepository.methods.invalidate}
    />
  );
}
