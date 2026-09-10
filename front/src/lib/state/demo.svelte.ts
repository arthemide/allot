/**
 * The public showroom, and how the app knows it is running in one.
 *
 * Armed by the /demo route before anything renders; from there
 * `$lib/services/api` routes every call to the in-memory backend instead of
 * the server. Nothing else changes: it is the same app, over a store that
 * lives and dies with the tab.
 */
class Demo {
	enabled = $state(false);
}

export const demo = new Demo();
