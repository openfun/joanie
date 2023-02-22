import '@testing-library/jest-dom/extend-expect'
import 'whatwg-fetch';
import {server} from "./mocks/server";


module.exports = async () => {
    process.env.TZ = 'UTC';
};

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
afterAll(() => server.close());
