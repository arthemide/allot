import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { version } from './package.json';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	// package.json is where the release process writes the version; the app
	// reads it from here rather than carrying a copy.
	define: { __APP_VERSION__: JSON.stringify(version) }
});
