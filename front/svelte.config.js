import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),

	kit: {
		// Static build served by app.py from front/dist.
		adapter: adapter({ pages: 'dist', assets: 'dist', fallback: 'index.html' })
	}
};

export default config;
