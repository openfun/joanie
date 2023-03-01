/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Product } from '../models/Product';

import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';

export class ProductsService {

  constructor(public readonly httpRequest: BaseHttpRequest) {}

  /**
   * API ViewSet for all interactions with products.
   * @returns Product
   * @throws ApiError
   */
  public productsRead({
    id,
  }: {
    /**
     * primary key for the record as UUID
     */
    id: string,
  }): CancelablePromise<Product> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/products/{id}/',
      path: {
        'id': id,
      },
    });
  }

}
