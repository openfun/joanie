/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Enrollment } from '../models/Enrollment';

import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';

export class EnrollmentsService {

  constructor(public readonly httpRequest: BaseHttpRequest) {}

  /**
   * API ViewSet for all interactions with enrollments.
   * @returns any
   * @throws ApiError
   */
  public enrollmentsList({
    courseRun,
    wasCreatedByOrder,
    page,
    pageSize,
  }: {
    courseRun?: string,
    wasCreatedByOrder?: string,
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
    results: Array<Enrollment>;
  }> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/enrollments/',
      query: {
        'course_run': courseRun,
        'was_created_by_order': wasCreatedByOrder,
        'page': page,
        'page_size': pageSize,
      },
    });
  }

  /**
   * API ViewSet for all interactions with enrollments.
   * @returns Enrollment
   * @throws ApiError
   */
  public enrollmentsCreate({
    data,
  }: {
    data: Enrollment,
  }): CancelablePromise<Enrollment> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/enrollments/',
      body: data,
    });
  }

  /**
   * API ViewSet for all interactions with enrollments.
   * @returns Enrollment
   * @throws ApiError
   */
  public enrollmentsRead({
    id,
  }: {
    id: string,
  }): CancelablePromise<Enrollment> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/enrollments/{id}/',
      path: {
        'id': id,
      },
    });
  }

  /**
   * API ViewSet for all interactions with enrollments.
   * @returns Enrollment
   * @throws ApiError
   */
  public enrollmentsUpdate({
    id,
    data,
  }: {
    id: string,
    data: Enrollment,
  }): CancelablePromise<Enrollment> {
    return this.httpRequest.request({
      method: 'PUT',
      url: '/enrollments/{id}/',
      path: {
        'id': id,
      },
      body: data,
    });
  }

  /**
   * API ViewSet for all interactions with enrollments.
   * @returns Enrollment
   * @throws ApiError
   */
  public enrollmentsPartialUpdate({
    id,
    data,
  }: {
    id: string,
    data: Enrollment,
  }): CancelablePromise<Enrollment> {
    return this.httpRequest.request({
      method: 'PATCH',
      url: '/enrollments/{id}/',
      path: {
        'id': id,
      },
      body: data,
    });
  }

}
