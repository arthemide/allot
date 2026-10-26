/**
 * The sources read in the user's browser, by the id the backend knows them
 * under (src/sources/registry.py).
 */
import * as afer from './afer.js';
import type { BrowserSource } from './bookmarklet.js';

export const BROWSER_SOURCES: Record<string, BrowserSource & { name: string }> = {
	afer: { name: 'Afer', hosts: afer.hosts, read: afer.read }
};

/** Whether a page of `origin` may hand over a reading of `source`. */
export function readsFrom(source: string, origin: string): boolean {
	const known = BROWSER_SOURCES[source];
	if (!known) return false;
	let host: string;
	try {
		host = new URL(origin).hostname;
	} catch {
		return false;
	}
	return known.hosts.some((h) => host === h || host.endsWith(`.${h}`));
}
