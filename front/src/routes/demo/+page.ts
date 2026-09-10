import { startDemo } from '$lib/services/demo';
import { demo } from '$lib/state/demo.svelte';

// Armed before anything renders, so `$lib/services/api` answers from the
// browser store rather than the server for every component below. The sample
// portfolio is laid out at the same time: the visitor lands in a full app.
demo.enabled = true;
startDemo();

export const prerender = true;
