import tseslint from "/root/.npm-global/lib/node_modules/@typescript-eslint/eslint-plugin/dist/index.js";
import tsParser from "/root/.npm-global/lib/node_modules/@typescript-eslint/parser/dist/index.js";

export default [
  {
    files: ["src/**/*.ts"],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaVersion: 2022, sourceType: "module" },
    },
    plugins: { "@typescript-eslint": tseslint },
    rules: {
      "@typescript-eslint/no-unused-vars": "warn",
    },
  },
];
