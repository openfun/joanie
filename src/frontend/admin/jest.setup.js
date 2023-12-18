import "@testing-library/jest-dom";
import "whatwg-fetch";
import { server } from "./mocks/server";

jest.mock("next/router", () => require("next-router-mock"));

// Establish API mocking before all tests.

beforeEach(() => {
  /**
   * If we don't delete `location` before reassign it, an error throws during tests:
   * `Attempted to log "TypeError: Cannot read properties of null (reading '_location')`
   */
  delete window.location;
  window.location = new URL("http://localhost:3000/");
  window.URL.createObjectURL = jest.fn();
});
beforeAll(() => {
  server.listen();
});

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests.
afterEach(() => {
  server.resetHandlers();
  window.URL.createObjectURL.mockReset();
});
// Clean up after the tests are finished.
afterAll(() => {
  server.close();
});
