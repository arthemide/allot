/**
 * Generic launcher for a source that is read in the user's own browser.
 *
 * A source hands it its reader (a function that knows the site's pages and
 * XPaths) and the Allot origin to send the result to. The launcher handles
 * everything that does not depend on the site: checking the domain, fetching
 * pages with the user's session, reporting progress, and handing the snapshot to Allot through a URL
 * fragment.
 *
 * `run` and the reader are serialised into one `javascript:` URL, so neither
 * may reference anything from its module. The tests compile each one on its
 * own.
 */

export interface SourceLine {
	label: string;
	isin?: string | null;
	quantity?: number | null;
	unit_cost?: number | null;
	invested?: number | null;
	unit_value?: number | null;
	valuation?: number | null;
	currency?: string | null;
	value_date?: string | null;
	by_amount?: boolean;
}

export interface SourceAccount {
	label: string;
	product?: string;
	balance?: number | null;
	available?: boolean;
	lines?: SourceLine[];
}

export interface SourceSnapshot {
	source: string;
	version: number;
	read_on: string;
	accounts: SourceAccount[];
}

export interface Io {
	fetch(url: string): Promise<Response>;
	go(url: string): void;
	say(message: string): void;
	here: string;
}

export type Reader = (io: Io) => Promise<SourceSnapshot>;

export async function run(
	reader: Reader,
	allot: string,
	// The site's domains: anywhere else, the reader would fetch the wrong pages
	// with whatever session that site holds.
	hosts: string[],
	// The bookmarklet passes nothing: the default is the page it runs on.
	// Declared here, not in the module, so it travels with the function.
	io: Io = {
		fetch: (url) => fetch(url, { credentials: 'include' }),
		go: (url) => location.assign(url),
		say: (message) => alert(message),
		here: location.href
	}
): Promise<void> {
	const show = (message: string) => {
		let status = document.getElementById('allot-status');
		if (!status) {
			status = document.createElement('div');
			status.id = 'allot-status';
			status.setAttribute(
				'style',
				'position:fixed;top:12px;right:12px;z-index:2147483647;padding:8px 12px;' +
					'background:#111;color:#fff;font:13px sans-serif;border-radius:6px'
			);
			document.body.appendChild(status);
		}
		status.textContent = `Allot - ${message}`;
	};

	// One request per page; the reader parses it and spots a lost session.
	const fetchOk = async (url: string) => {
		const response = await io.fetch(url);
		if (!response.ok) throw new Error(`${response.status} on ${new URL(url).pathname}`);
		return response;
	};

	const host = new URL(io.here).hostname;
	if (!hosts.some((h) => host === h || host.endsWith(`.${h}`))) {
		io.say(`Allot reads ${hosts.join(', ')} only. Open it, log in, then click the bookmark.`);
		return;
	}

	try {
		show('reading...');
		const snapshot = await reader({ ...io, fetch: fetchOk });
		show('opening Allot...');
		io.go(`${allot}/import/#${encodeURIComponent(JSON.stringify(snapshot))}`);
	} catch (error) {
		io.say(
			`Allot could not read this site: ${error instanceof Error ? error.message : String(error)}`
		);
	}
}

/** A source as the launcher takes it: where it is read, and how. */
export interface BrowserSource {
	hosts: string[];
	read: Reader;
}

/** The code the bookmark (or the console) runs: the launcher, the reader, this instance. */
export function launcherCode(source: BrowserSource, allot: string): string {
	const args = [source.read.toString(), JSON.stringify(allot), JSON.stringify(source.hosts)];
	return `(${run.toString()})(${args.join(', ')})`;
}

export function bookmarkletHref(source: BrowserSource, allot: string): string {
	return 'javascript:' + encodeURIComponent(`void ${launcherCode(source, allot)}`);
}
