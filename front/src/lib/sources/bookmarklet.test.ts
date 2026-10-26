/**
 * The bookmarklet, run the way a browser runs it.
 *
 * The launcher and the Afer reader are serialised and evaluated outside any
 * module, with the browser globals stubbed: anything they still borrowed from
 * their module would be a ReferenceError here, as it is on Afer's site. The
 * DOM is a stub that answers XPaths by substring, enough to walk one contract
 * with one fund.
 */
import { describe, expect, it } from 'vitest';

import * as afer from './afer.js';
import { bookmarkletHref, launcherCode, READING, READY } from './bookmarklet.js';
import { readsFrom } from './index.js';
import { decode, validate } from './payload.js';

const ALLOT = 'https://allot.example.com';
const AFER = 'https://adherent.gie-afer.fr/espaceadherent/Accueil';

type Answer = string | { value: string } | Answer[] | null;

const PAGES: Record<string, [string, Answer][]> = {
	summary: [
		['o-product-roundels', [null]],
		['o-product-tab-category', 'Épargne'],
		['a-heading', 'Afer Multisupport'],
		['/@href', { value: '/espaceadherent/Contrat/1' }]
	],
	detail: [
		['Type de produit', 'Assurance vie'],
		['h3[contains(text(), "Valeur de rachat")]', '12 345,67 €'],
		['m-table', [null]],
		['"Nom du su")]/a', 'Afer Actions Monde C/D'],
		['"Nombre de parts"', '4,0000'],
		['"Valeur de la part"', '50,00 €'],
		['td[contains(@data-label, "Valeur de rachat")]', '200,00 €'],
		['"Prime investie"', '160,00 €'],
		['"Date de valeur"', '14/10/2026']
	]
};

const CONTRACT = [
	{
		label: 'Afer Multisupport',
		product: 'Assurance vie',
		balance: 12345.67,
		available: true,
		lines: [
			{
				label: 'Afer Actions Monde C/D',
				quantity: 4,
				unit_value: 50,
				valuation: 200,
				invested: 160,
				value_date: '2026-10-14',
				by_amount: true
			}
		]
	}
];

function stubDocument(name: string, xpaths: string[]) {
	const doc = {
		querySelector: (selector: string) =>
			name === 'login' && selector === 'form#loginForm' ? {} : null,
		evaluate(xpath: string) {
			xpaths.push(xpath);
			const answer = (PAGES[name] ?? []).find(([key]) => xpath.includes(key))?.[1] ?? null;
			const node = (value: Answer) =>
				typeof value === 'string'
					? { ownerDocument: doc, textContent: value }
					: { ownerDocument: doc, ...value };
			const nodes = Array.isArray(answer) ? answer.map(node) : answer === null ? [] : [node(answer)];
			return {
				singleNodeValue: nodes[0] ?? null,
				snapshotLength: nodes.length,
				snapshotItem: (i: number) => nodes[i]
			};
		}
	};
	return doc;
}

/** How the Allot tab the click opens behaves. */
type Tab = 'answers' | 'impostor' | 'silent' | 'blocked';

/**
 * Click the bookmark. The tab says it is ready, only other pages say so, it
 * never answers (the site cut it off from its opener), or it is blocked as a
 * pop-up.
 */
async function click(
	code: string,
	{ summary = 'summary', here = `${AFER}/Synthese-Contrats`, tab = 'answers' as Tab } = {}
) {
	const xpaths: string[] = [];
	const said: string[] = [];
	const posted: { message: { type: string; snapshot: unknown }; origin: string }[] = [];
	const handlers: ((event: unknown) => void)[] = [];
	let went = '';
	let opened = '';
	let closed = false;
	const target = {
		postMessage: (message: never, origin: string) => posted.push({ message, origin }),
		close: () => (closed = true)
	};
	const context = {
		URL,
		location: { href: here, assign: (url: string) => (went = url) },
		alert: (message: string) => said.push(message),
		window: {
			open: (url: string) => {
				if (tab === 'blocked') return null;
				opened = url;
				if (tab === 'answers' || tab === 'impostor') {
					// The tab loads, then says it is ready; impostors say so too.
					queueMicrotask(() => {
						const ready = { data: { type: READY } };
						for (const handler of [...handlers]) {
							handler({ ...ready, origin: 'https://evil.example', source: target });
							handler({ ...ready, origin: ALLOT, source: {} });
							if (tab === 'answers') handler({ ...ready, origin: ALLOT, source: target });
						}
					});
				}
				return target;
			}
		},
		addEventListener: (_: string, handler: (event: unknown) => void) => handlers.push(handler),
		removeEventListener: (_: string, handler: (event: unknown) => void) =>
			handlers.splice(handlers.indexOf(handler), 1),
		// Patience runs out at once when the tab is silent, never otherwise.
		setTimeout: (resolve: () => void) => (tab === 'answers' ? undefined : resolve()),
		fetch: async (url: string) => ({
			ok: true,
			status: 200,
			text: async () => (url.endsWith('Synthese-Contrats') ? summary : 'detail')
		}),
		DOMParser: class {
			parseFromString(page: string) {
				return stubDocument(page, xpaths);
			}
		},
		document: {
			getElementById: () => null,
			createElement: () => ({ setAttribute() {} }),
			body: { appendChild() {} }
		}
	};
	// A Function body sees only globals and its parameters, never this module.
	const names = Object.keys(context);
	new Function(...names, code)(...names.map((name) => context[name as keyof typeof context]));
	// The bookmark's `void` drops the promise: let every stubbed call settle.
	await new Promise((resolve) => setTimeout(resolve, 0));
	return { went, said, xpaths, posted, opened, closed, listening: handlers.length };
}

describe('the Afer bookmarklet', () => {
	it('posts the reading to the Allot tab, never through a URL', async () => {
		const { went, said, posted, opened, listening } = await click(launcherCode(afer, ALLOT));
		expect(said).toEqual([]);
		expect(opened).toBe(`${ALLOT}/import/`);
		expect(went).toBe('');
		// Once, to the tab that said it was ready, and to Allot's origin only
		expect(posted).toHaveLength(1);
		expect(posted[0].origin).toBe(ALLOT);
		expect(posted[0].message.type).toBe(READING);
		expect(validate(posted[0].message.snapshot).accounts).toEqual(CONTRACT);
		expect(listening).toBe(0);
	});

	it('falls back to the URL when the tab never answers', async () => {
		const { went, posted, closed } = await click(launcherCode(afer, ALLOT), { tab: 'silent' });
		expect(posted).toEqual([]);
		expect(closed).toBe(true);
		expect(went.startsWith(`${ALLOT}/import/#`)).toBe(true);
		expect(decode(went.slice(went.indexOf('#'))).accounts).toEqual(CONTRACT);
	});

	it('hands nothing over to a page that is not the tab it opened', async () => {
		const { posted } = await click(launcherCode(afer, ALLOT), { tab: 'impostor' });
		expect(posted).toEqual([]);
	});

	it('says so when the pop-up is blocked, before reading anything', async () => {
		const { said, xpaths } = await click(launcherCode(afer, ALLOT), { tab: 'blocked' });
		expect(xpaths).toEqual([]);
		expect(said).toEqual([expect.stringContaining('Allow pop-ups')]);
	});

	it('asks only valid class tests', async () => {
		const { xpaths } = await click(launcherCode(afer, ALLOT));
		expect(xpaths.some((x) => x.includes('o-product-tab-category'))).toBe(true);
		expect(xpaths.filter((x) => /\)\(|has-class/.test(x))).toEqual([]);
	});

	it('says so when the Afer session has ended', async () => {
		const { posted, said, closed } = await click(launcherCode(afer, ALLOT), { summary: 'login' });
		expect(posted).toEqual([]);
		expect(closed).toBe(true);
		expect(said).toEqual([expect.stringContaining('the Afer session has ended')]);
	});

	it('refuses to read another site', async () => {
		// gie-afer.fr.evil.com ends with the name, not with the domain
		const { opened, said, xpaths } = await click(launcherCode(afer, ALLOT), {
			here: 'https://gie-afer.fr.evil.com/'
		});
		expect(opened).toBe('');
		expect(xpaths).toEqual([]);
		expect(said).toEqual([expect.stringContaining('reads gie-afer.fr only')]);
	});

	it('runs the same code from the bookmark', async () => {
		const href = bookmarkletHref(afer, ALLOT);
		expect(href.startsWith('javascript:')).toBe(true);
		const { posted } = await click(decodeURIComponent(href.slice('javascript:'.length)));
		expect(posted).toHaveLength(1);
	});
});

describe('who may hand over a reading', () => {
	it.each([
		['https://adherent.gie-afer.fr', true],
		['https://gie-afer.fr', true],
		['https://gie-afer.fr.evil.com', false],
		['null', false]
	])('afer from %s: %s', (origin, allowed) => {
		expect(readsFrom('afer', origin)).toBe(allowed);
	});

	it('refuses a source it does not know', () => {
		expect(readsFrom('bourso', 'https://clients.boursobank.com')).toBe(false);
	});
});
