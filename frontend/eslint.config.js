import security from 'eslint-plugin-security';
import globals from 'globals';

// SAST gate for the frontend (ISSUE 2.6 / FedRAMP SI-3, SA-11). Every
// `security/*` finding is treated as an error so `npm run lint` — and
// therefore CI — fails on any HIGH-risk pattern (eval, unsafe regex, child
// processes, non-literal fs paths, etc.).
const securityRules = Object.fromEntries(
  Object.keys(security.configs.recommended.rules).map((rule) => [rule, 'error']),
);

export default [
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
  {
    files: ['**/*.{js,jsx}'],
    plugins: { security },
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: securityRules,
  },
];
