// Add any custom config to be passed to Jest
/** @type {import('jest').Config} */
const customJestConfig = {
  // Add more setup options before each test is run
  resetMocks: true,
  setupFiles: ["<rootDir>/jest.env.js"],
  setupFilesAfterEnv: [
    "./jest.polyfills.js",
    "@testing-library/jest-dom",
    "<rootDir>/jest.setup.js",
  ],
  // if using TypeScript with a baseUrl set to the root directory then you need the below for alias' to work
  moduleDirectories: ["node_modules", "<rootDir>/"],

  // If you're using [Module Path Aliases](https://nextjs.org/docs/advanced-features/module-path-aliases),
  // you will have to add the moduleNameMapper in order for jest to resolve your absolute paths.
  // The paths have to be matching with the paths option within the compilerOptions in the tsconfig.json
  // For example:
  moduleNameMapper: {
    "@/(.*)$": "<rootDir>/src/$1",
  },
  testEnvironmentOptions: {
    customExportConditions: [""],
  },
  testEnvironment: "jest-environment-jsdom",
  transformIgnorePatterns: [
    "/node_modules/(?!(" +
      "jest-next-dynamic|" +
      "query-string|" +
      "decode-uri-component|" +
      "split-on-first|" +
      "filter-obj|" +
      "@uiw/react-md-editor|" +
      "@uiw/react-markdown-preview|" +
      "devlop|" +
      "html-url-attributes|" +
      "longest-streak|" +
      "react-markdown|" +
      "trim-lines|" +
      "@mdx-js/mdx2|" +
      "unified|" +
      "bail|" +
      "is-plain-obj|" +
      "trough|" +
      "vfile[^/]*|" +
      "unist-util-stringify-position|" +
      "remark-mdx|" +
      "micromark[^/]*|" +
      "unist-util-position-from-estree|" +
      "estree-util[^/]+|" +
      "estree-walker|" +
      "decode-named-character-reference|" +
      "character-entities|" +
      "mdast-util[^/]+|" +
      "ccount|" +
      "parse-entities|" +
      "character-entities-legacy|" +
      "character-reference-invalid|" +
      "stringify-entities|" +
      "character-entities-html4|" +
      "remark[^/]+|" +
      "unist-builder|" +
      "unist-util[^/]+|" +
      "property-information|" +
      "github-slugger|" +
      "refractor|" +
      "periscopic|" +
      "is-decimal|" +
      "is-hexadecimal|" +
      "is-alphanumerical|" +
      "is-alphabetical|" +
      "direction|" +
      "bcp-47-match|" +
      "is-reference|" +
      "hast-util[^/]+|" +
      "nth-check|" +
      "hast-to-hyperscript+|" +
      "html-void-elements+|" +
      "comma-separated-tokens|" +
      "space-separated-tokens|" +
      "zwitch|" +
      "rehype-[^/]+|" +
      "hastscript|" +
      "web-namespaces|" +
      "escape-string-regexp|" +
      "markdown-table|" +
      "rehype",
    ")/)",
    "^.+\\.module\\.(css|sass|scss)$",
  ],
};

const nextJest = require("next/jest");

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: "./",
});

module.exports = async (...args) => {
  const createConfig = createJestConfig(customJestConfig);
  const config = await createConfig(...args);

  config.transformIgnorePatterns = customJestConfig.transformIgnorePatterns;

  return config;
};
