/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Order } from '../models/Order';
import type { OrderAbortBody } from '../models/OrderAbortBody';
import type { OrderCreate } from '../models/OrderCreate';
import type { OrderCreateResponse } from '../models/OrderCreateResponse';

import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';

export class OrdersService {

  constructor(public readonly httpRequest: BaseHttpRequest) {}

  /**
   * API view for a user to consult the orders he/she owns or create a new one.
   * GET /api/orders/
   * Return list of all orders for a user with pagination
   *
   * POST /api/orders/ with expected data:
   * - course: course code
   * - product: product id (product must be associated to the course. Otherwise,
   * a 400 error is returned)
   * Return new order just created
   * @returns any
   * @throws ApiError
   */
  public ordersList({
    product,
    course,
    state,
    page,
    pageSize,
  }: {
    product?: string,
    course?: string,
    state?: string,
    /**
     * A page number within the paginated result set.
     */
    page?: number,
    /**
     * Number of results to return per page.
     */
    pageSize?: number,
  }): CancelablePromise<{
    count: number;
    next?: string | null;
    previous?: string | null;
    results: Array<Order>;
  }> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/orders/',
      query: {
        'product': product,
        'course': course,
        'state': state,
        'page': page,
        'page_size': pageSize,
      },
    });
  }

  /**
   * Try to create an order and a related payment if the payment is fee.
   * @returns OrderCreateResponse
   * @throws ApiError
   */
  public ordersCreate({
    data,
  }: {
    data: OrderCreate,
  }): CancelablePromise<OrderCreateResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/orders/',
      body: data,
    });
  }

  /**
   * API view for a user to consult the orders he/she owns or create a new one.
   * GET /api/orders/
   * Return list of all orders for a user with pagination
   *
   * POST /api/orders/ with expected data:
   * - course: course code
   * - product: product id (product must be associated to the course. Otherwise,
   * a 400 error is returned)
   * Return new order just created
   * @returns Order
   * @throws ApiError
   */
  public ordersRead({
    id,
  }: {
    id: string,
  }): CancelablePromise<Order> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/orders/{id}/',
      path: {
        'id': id,
      },
    });
  }

  /**
   * Abort a pending order and the related payment if there is one.
   * @returns void
   * @throws ApiError
   */
  public ordersAbort({
    id,
    data,
  }: {
    id: string,
    data: OrderAbortBody,
  }): CancelablePromise<void> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/orders/{id}/abort/',
      path: {
        'id': id,
      },
      body: data,
    });
  }

  /**
   * Retrieve an invoice through its reference if it is related to
   * the order instance and owned by the authenticated user.
   * @returns binary File Attachment
   * @throws ApiError
   */
  public ordersInvoice({
    id,
    reference,
  }: {
    id: string,
    reference: string,
  }): CancelablePromise<Blob> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/orders/{id}/invoice/',
      path: {
        'id': id,
      },
      query: {
        'reference': reference,
      },
    });
  }

}
