import formatjs from "eslint-plugin-formatjs";
import typescriptEslint from "@typescript-eslint/eslint-plugin";
import globals from "globals";
import tsParser from "@typescript-eslint/parser";
import path from "node:path";
import { fileURLToPath } from "node:url";
import js from "@eslint/js";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
    baseDirectory: __dirname,
    recommendedConfig: js.configs.recommended,
    allConfig: js.configs.all
});

export default [...compat.extends(
    "next/core-web-vitals",
    "airbnb",
    "airbnb-typescript",
    "plugin:compat/recommended",
    "plugin:prettier/recommended",
), {
    plugins: {
        formatjs,
        "@typescript-eslint": typescriptEslint,
    },
    languageOptions: {
        globals: {
            ...globals.browser,
            ...globals.jest,
        },
        parser: tsParser,
        ecmaVersion: 5,
        sourceType: "script",
        parserOptions: {
            projectService: {
                defaultProject: "./tsconfig.json",
            },

            ecmaFeatures: {
                jsx: true,
            },
        },
    },
    settings: {
        polyfills: ["fetch", "Promise"],
        "import/resolver": "webpack",
    },
    rules: {
        "@typescript-eslint/explicit-member-accessibility": ["error", {
            accessibility: "no-public",
        }],
        "import/no-extraneous-dependencies": ["error", {
            devDependencies: [
                "./src/tests/**",
                "./src/components/testing/*",
                "**/*.?(test|spec).e2e.[jt]s?(x)",
                "**/*.?(spec|test).[jt]s?(x)",
            ],
        }],
        "react-hooks/exhaustive-deps": "off",
        "no-restricted-imports": ["error", {
            paths: ["@mui/material"],
            patterns: ["@mui/material/*/*"],
        }],
        "@typescript-eslint/lines-between-class-members": "off",
        "@typescript-eslint/no-use-before-define": "off",
        "@typescript-eslint/no-throw-literal": "off",
        "arrow-parens": "error",
        "consistent-return": "off",
        "default-case": "off",
        "formatjs/no-multiple-whitespaces": "error",
        "formatjs/enforce-description": "error",
        "formatjs/enforce-default-message": "error",
        "global-require": "off",
        "import/extensions": "off",
        "import/no-cycle": ["off"],
        "import/no-dynamic-require": "off",
        "import/order": ["error", {
            groups: ["builtin", "external", "internal", "parent", "sibling", "index"],
            alphabetize: { order: "ignore" }
        }],
        "import/prefer-default-export": "off",
        "jsx-a11y/click-events-have-key-events": "off",
        "jsx-a11y/label-has-associated-control": "warn",
        "no-console": ["error", { allow: ["warn"] }],
        "no-else-return": "off",
        "no-empty-function": "off",
        "no-nested-ternary": "warn",
        "no-param-reassign": "off",
        "no-plusplus": "off",
        "no-promise-executor-return": "off",
        "no-prototype-builtins": "off",
        "no-return-assign": "off",
        "no-return-await": "off",
        "no-undef": "off",
        "no-underscore-dangle": "off",
        "no-useless-escape": "off",
        "prefer-template": "off",
        "react/button-has-type": "off",
        "class-methods-use-this": "off",
        "react/destructuring-assignment": "off",
        "react/jsx-boolean-value": "off",
        "react/jsx-fragments": "off",
        "react/jsx-props-no-spreading": "off",
        "react/jsx-uses-react": "off",
        "react/no-array-index-key": "warn",
        "react/prop-types": "off",
        "react/react-in-jsx-scope": "off",
        "react/require-default-props": "off",
        "react/style-prop-object": ["error", { allow: ["FormattedNumber"] }],
    },
}];
