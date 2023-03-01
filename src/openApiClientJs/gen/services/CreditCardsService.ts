/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CreditCard } from '../models/CreditCard';

import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';

export class CreditCardsService {

  constructor(public readonly httpRequest: BaseHttpRequest) {}

  /**
   * API views allows to get all credit cards, update or delete one
   * for the authenticated user.
   * GET /api/credit-cards/
   * Return the list of all credit cards owned by the authenticated user
   *
   * PUT /api/credit-cards/<credit_card_id> with expected data:
   * - title: str
   * - is_main?: bool
   *
   * DELETE /api/credit-cards/<credit_card_id>
   * Delete the selected credit card
   * @returns any
   * @throws ApiError
   */
  public creditCardsList({
    page,
  }: {
    /**
     * A page number within the paginated result set.
     */
    page?: number,
  }): CancelablePromise<{
    count: number;
    next?: string | null;
    previous?: string | null;
    results: Array<CreditCard>;
  }> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/credit-cards/',
      query: {
        'page': page,
      },
    });
  }

  /**
   * API views allows to get all credit cards, update or delete one
   * for the authenticated user.
   * GET /api/credit-cards/
   * Return the list of all credit cards owned by the authenticated user
   *
   * PUT /api/credit-cards/<credit_card_id> with expected data:
   * - title: str
   * - is_main?: bool
   *
   * DELETE /api/credit-cards/<credit_card_id>
   * Delete the selected credit card
   * @returns CreditCard
   * @throws ApiError
   */
  public creditCardsRead({
    id,
  }: {
    id: string,
  }): CancelablePromise<CreditCard> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/credit-cards/{id}/',
      path: {
        'id': id,
      },
    });
  }

  /**
   * API views allows to get all credit cards, update or delete one
   * for the authenticated user.
   * GET /api/credit-cards/
   * Return the list of all credit cards owned by the authenticated user
   *
   * PUT /api/credit-cards/<credit_card_id> with expected data:
   * - title: str
   * - is_main?: bool
   *
   * DELETE /api/credit-cards/<credit_card_id>
   * Delete the selected credit card
   * @returns CreditCard
   * @throws ApiError
   */
  public creditCardsUpdate({
    id,
    data,
  }: {
    id: string,
    data: CreditCard,
  }): CancelablePromise<CreditCard> {
    return this.httpRequest.request({
      method: 'PUT',
      url: '/credit-cards/{id}/',
      path: {
        'id': id,
      },
      body: data,
    });
  }

  /**
   * API views allows to get all credit cards, update or delete one
   * for the authenticated user.
   * GET /api/credit-cards/
   * Return the list of all credit cards owned by the authenticated user
   *
   * PUT /api/credit-cards/<credit_card_id> with expected data:
   * - title: str
   * - is_main?: bool
   *
   * DELETE /api/credit-cards/<credit_card_id>
   * Delete the selected credit card
   * @returns CreditCard
   * @throws ApiError
   */
  public creditCardsPartialUpdate({
    id,
    data,
  }: {
    id: string,
    data: CreditCard,
  }): CancelablePromise<CreditCard> {
    return this.httpRequest.request({
      method: 'PATCH',
      url: '/credit-cards/{id}/',
      path: {
        'id': id,
      },
      body: data,
    });
  }

  /**
   * API views allows to get all credit cards, update or delete one
   * for the authenticated user.
   * GET /api/credit-cards/
   * Return the list of all credit cards owned by the authenticated user
   *
   * PUT /api/credit-cards/<credit_card_id> with expected data:
   * - title: str
   * - is_main?: bool
   *
   * DELETE /api/credit-cards/<credit_card_id>
   * Delete the selected credit card
   * @returns void
   * @throws ApiError
   */
  public creditCardsDelete({
    id,
  }: {
    id: string,
  }): CancelablePromise<void> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/credit-cards/{id}/',
      path: {
        'id': id,
      },
    });
  }

}
