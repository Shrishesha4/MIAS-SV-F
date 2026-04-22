import prettier from 'eslint-config-prettier';
import path from 'node:path';
import { includeIgnoreFile } from '@eslint/compat';
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import { defineConfig } from 'eslint/config';
import globals from 'globals';
import ts from 'typescript-eslint';
import svelteConfig from './svelte.config.js';

const gitignorePath = path.resolve(import.meta.dirname, '../.gitignore');

export default defineConfig(
	includeIgnoreFile(gitignorePath),
	js.configs.recommended,
	...ts.configs.recommended,
	...svelte.configs.recommended,
	prettier,
	...svelte.configs.prettier,
	{
		languageOptions: { globals: { ...globals.browser, ...globals.node } },
		rules: {
			// typescript-eslint strongly recommend that you do not use the no-undef lint rule on TypeScript projects.
			// see: https://typescript-eslint.io/troubleshooting/faqs/eslint/#i-get-errors-from-the-no-undef-rule-about-global-variables-not-being-defined-even-though-there-are-no-typescript-errors
			'no-undef': 'off'
		}
	},
	{
		files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: {
			parserOptions: {
				projectService: true,
				extraFileExtensions: ['.svelte'],
				parser: ts.parser,
				svelteConfig
			}
		},
		rules: {
			// ── Svelte 5 rune enforcement ─────────────────────────────────────────
			// Ban Svelte 4 reactive-statement syntax ($: label).
			'svelte/no-reactive-functions': 'error',
			'svelte/no-reactive-literals': 'error',
			'svelte/no-immutable-reactive-statements': 'error',
			'svelte/no-reactive-reassign': 'error',
			// Ban use of Svelte internals.
			'svelte/no-svelte-internal': 'error',
			// Ban Svelte 4 "export let" prop declarations — use $props() instead.
			'no-restricted-syntax': [
				'error',
				{
					// export let foo / export let foo = default inside a .svelte <script>
					selector:
						'ExportNamedDeclaration > VariableDeclaration[kind="let"]',
					message:
						'Svelte 4 "export let" props are banned. Use "$props()" rune instead.',
				},
				{
					// <slot> elements — use Snippet + {@render} instead.
					selector:
						'SvelteElement[name.name="slot"]',
					message:
						'Svelte 4 <slot> is banned. Use Snippet + {@render children()} instead.',
				},
			],
		}
	}
);
