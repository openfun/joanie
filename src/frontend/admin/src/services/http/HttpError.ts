/**
 * An error to raise when a request failed.
 * It has been designed to store response.status and response.statusText.
 */
export class HttpError extends Error {
  code: number;
  data: any;

  constructor(status: number, statusText: string, data: any) {
    super(statusText);
    this.code = status;
    this.data = data;
  }
}
