/**
 * Generic launcher for a source that is read in the user's own browser.
 *
 * A source hands it its reader (a function that knows the site's pages and
 * XPaths) and the Allot origin to send the result to. The launcher handles
 * everything that does not depend on the site: checking the domain, fetching
 * pages with the user's session, reporting progress, and handing the snapshot
 * to Allot.
 *
 * The hand-over is a postMessage to the Allot tab the click opens, once that
 * tab says it is ready: the reading never sits in a URL, so it never reaches
 * the browser history. Only when the tab never answers - a site can cut the
 * tabs it opens off from itself - does the reading fall back to a URL
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

/** What a reader needs: the page it runs on, and the user's session. */
export interface ReadIo {
	fetch(url: string): Promise<Response>;
	here: string;
}

/** Something a reading can be posted to: the Allot window the launcher opened. */
export interface MessageTarget {
	postMessage(message: unknown, targetOrigin: string): void;
	close?(): void;
}

/** What the launcher needs on top: a window to open, and a way to talk to it. */
export interface Io extends ReadIo {
	open(url: string): MessageTarget | null;
	listen(handler: (event: MessageEvent) => void): () => void;
	go(url: string): void;
	say(message: string): void;
	wait(ms: number): Promise<void>;
}

export type Reader = (io: ReadIo) => Promise<SourceSnapshot>;

/** The messages between the launcher and /import, both ways. */
export const READY = 'allot-ready';
export const READING = 'allot-reading';

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
		here: location.href,
		// Named, so a second click reuses the tab the first one opened.
		open: (url) => window.open(url, 'allot-import'),
		listen: (handler) => {
			addEventListener('message', handler);
			return () => removeEventListener('message', handler);
		},
		go: (url) => location.assign(url),
		say: (message) => alert(message),
		wait: (ms) => new Promise((resolve) => setTimeout(resolve, ms))
	}
): Promise<void> {
	// Long enough to log into Allot first, when it asks.
	const PATIENCE = 120_000;
	// Messages are typed by these; `run` cannot read the module's constants.
	const ready = 'allot-ready';
	const reading = 'allot-reading';

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

	// Opened now, while the click still counts as one: after the reading's
	// requests, the browser would take it for an unwanted pop-up.
	const origin = new URL(allot).origin;
	const target = io.open(`${allot}/import/`);
	if (!target) {
		io.say('Allot could not open its tab. Allow pop-ups on this site, then click again.');
		return;
	}
	let stop = () => {};
	const answered = new Promise<boolean>((resolve) => {
		stop = io.listen((event) => {
			if (event.origin === origin && event.source === target && event.data?.type === ready) {
				resolve(true);
			}
		});
	});

	try {
		show('reading...');
		const snapshot = await reader({ fetch: fetchOk, here: io.here });
		show('handing the reading to the Allot tab...');
		const handed = await Promise.race([answered, io.wait(PATIENCE).then(() => false)]);
		if (handed) {
			// To Allot's origin only: no other page gets to read the amounts.
			target.postMessage({ type: reading, snapshot }, origin);
			show('done. The reading is in the Allot tab.');
		} else {
			// The tab never answered: this site cuts it off from its opener.
			// The URL carries the reading instead, and lands in the history.
			target.close?.();
			io.go(`${allot}/import/#${encodeURIComponent(JSON.stringify(snapshot))}`);
		}
	} catch (error) {
		target.close?.();
		io.say(
			`Allot could not read this site: ${error instanceof Error ? error.message : String(error)}`
		);
	} finally {
		stop();
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
