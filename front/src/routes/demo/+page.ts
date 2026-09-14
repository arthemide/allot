import { startDemo } from '$lib/services/demo';

// The sample portfolio is laid out before anything renders: the visitor
// lands in a full app. Which backend answers is decided by the route itself,
// in $lib/state/demo.svelte.ts.
startDemo();
