import "@testing-library/jest-dom/extend-expect";
import "whatwg-fetch";
import { cleanup } from "@testing-library/react";
import { server } from "./mocks/server";
import {jest} from '@jest/globals';

(global as any).jest = jest;

// Establish API mocking before all tests.
beforeAll(() => {
  server.listen();
});

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests.
afterEach(() => {
  server.resetHandlers();
});
// Clean up after the tests are finished.
afterAll(() => {
  server.close();
  cleanup();
});

export default {}
