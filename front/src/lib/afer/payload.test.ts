import { describe, expect, it } from 'vitest';

import { decode, prum, shape } from './payload.js';
import type { SourceSnapshot } from '../sources/bookmarklet.js';

const snapshot: SourceSnapshot = {
	source: 'afer',
	version: 1,
	read_on: '2026-10-14',
	accounts: [
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
					value_date: null
				}
			]
		}
	]
};

describe('the Afer reading', () => {
	it('decodes what the bookmarklet sends', () => {
		expect(decode(`#${encodeURIComponent(JSON.stringify(snapshot))}`)).toEqual(snapshot);
	});

	it.each([
		['not JSON', '#%7Bnope', 'does not carry'],
		['another source', `#${encodeURIComponent('{"source":"bourso"}')}`, 'unexpected shape'],
		[
			'a line with text for a number',
			`#${encodeURIComponent(
				JSON.stringify({
					...snapshot,
					accounts: [
						{ ...snapshot.accounts[0], lines: [{ ...snapshot.accounts[0].lines![0], quantity: '4' }] }
					]
				})
			)}`,
			'unexpected shape'
		]
	])('refuses %s', (_, fragment, message) => {
		expect(() => decode(fragment)).toThrow(message);
	});

	it('derives the PRUM from what was paid in', () => {
		expect(prum(snapshot.accounts[0].lines![0])).toBe(40);
		expect(prum({ ...snapshot.accounts[0].lines![0], invested: null })).toBeNull();
	});

	it('describes the reading without an amount', () => {
		const report = shape(snapshot);
		expect(report).toContain('"Afer Actions Monde C/D": quantity=yes');
		expect(report).toContain('invested=yes');
		expect(report).not.toMatch(/12345|200|160/);
	});
});
