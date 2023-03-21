/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Address } from './Address';

export type OrderCreate = {
  credit_card_id?: string;
  course: string;
  organization?: string;
  owner: string;
  product: string;
  billing_address?: Address;
};

