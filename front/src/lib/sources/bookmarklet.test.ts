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

import { decode } from './payload.js';
import * as afer from './afer.js';
import { bookmarkletHref, launcherCode } from './bookmarklet.js';

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

function stubDocument(name: string, xpaths: string[]) {
	const doc = {
		querySelector: (selector: string) => (name === 'login' && selector === 'form#loginForm' ? {} : null),
		evaluate(xpath: string) {
			xpaths.push(xpath);
			const answer = (PAGES[name] ?? []).find(([key]) => xpath.includes(key))?.[1] ?? null;
			const node = (value: Answer) =>
				typeof value === 'string' ? { ownerDocument: doc, textContent: value } : { ownerDocument: doc, ...value };
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

async function click(code: string, summary = 'summary', here = `${AFER}/Synthese-Contrats`) {
	const xpaths: string[] = [];
	const said: string[] = [];
	let went = '';
	const context = {
		URL,
		location: { href: here, assign: (url: string) => (went = url) },
		alert: (message: string) => said.push(message),
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
	// The bookmark's `void` drops the promise: let every stubbed fetch settle.
	await new Promise((resolve) => setTimeout(resolve, 0));
	return { went, said, xpaths };
}

describe('the Afer bookmarklet', () => {
	it('reads a contract and opens Allot with it', async () => {
		const { went, said } = await click(launcherCode(afer, ALLOT));
		expect(said).toEqual([]);
		expect(went.startsWith(`${ALLOT}/import/#`)).toBe(true);
		const snapshot = decode(went.slice(went.indexOf('#')));
		expect(snapshot.accounts).toEqual([
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
		]);
	});

	it('asks only valid class tests', async () => {
		const { xpaths } = await click(launcherCode(afer, ALLOT));
		expect(xpaths.some((x) => x.includes('o-product-tab-category'))).toBe(true);
		expect(xpaths.filter((x) => /\)\(|has-class/.test(x))).toEqual([]);
	});

	it('says so when the Afer session has ended', async () => {
		const { went, said } = await click(launcherCode(afer, ALLOT), 'login');
		expect(went).toBe('');
		expect(said).toEqual([expect.stringContaining('the Afer session has ended')]);
	});

	it('refuses to read another site', async () => {
		// gie-afer.fr.evil.com ends with the name, not with the domain
		const { went, said, xpaths } = await click(
			launcherCode(afer, ALLOT),
			'summary',
			'https://gie-afer.fr.evil.com/'
		);
		expect(went).toBe('');
		expect(xpaths).toEqual([]);
		expect(said).toEqual([expect.stringContaining('reads gie-afer.fr only')]);
	});

	it('runs the same code from the bookmark', async () => {
		const href = bookmarkletHref(afer, ALLOT);
		expect(href.startsWith('javascript:')).toBe(true);
		const { went } = await click(decodeURIComponent(href.slice('javascript:'.length)));
		expect(went.startsWith(`${ALLOT}/import/#`)).toBe(true);
	});
});
