import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { version } from './package.json';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			preprocess: vitePreprocess(),
			// Static build served by app.py from front/dist.
			adapter: adapter({ pages: 'dist', assets: 'dist', fallback: 'index.html' })
		})
	],
	// package.json is where the release process writes the version; the app
	// reads it from here rather than carrying a copy.
	define: { __APP_VERSION__: JSON.stringify(version) }
});
