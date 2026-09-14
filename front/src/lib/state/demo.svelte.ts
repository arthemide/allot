/**
 * The public showroom, and how the app knows it is running in one.
 *
 * Read off the route rather than set by it: a flag posed on arrival would
 * outlive a client-side navigation back to the real app and hand it the
 * demo store. From here `$lib/services/api` routes every call to the
 * in-memory backend instead of the server. Nothing else changes: it is the
 * same app, over a store that lives and dies with the tab.
 */
import { page } from '$app/state';

class Demo {
	enabled = $derived(page.url.pathname.startsWith('/demo'));
}

export const demo = new Demo();
