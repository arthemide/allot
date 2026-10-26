import { describe, expect, it } from 'vitest';

import { decode, prum, shape } from './payload.js';
import type { SourceSnapshot } from './bookmarklet.js';

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

describe('a source reading', () => {
	it('decodes what the bookmarklet sends', () => {
		expect(decode(`#${encodeURIComponent(JSON.stringify(snapshot))}`)).toEqual(snapshot);
	});

	it.each([
		['not JSON', '#%7Bnope', 'does not carry'],
		['a reading without accounts', `#${encodeURIComponent('{"source":"afer"}')}`, 'unexpected shape'],
		['a reading without a source', `#${encodeURIComponent('{"version":1,"accounts":[]}')}`, 'unexpected shape'],
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

	it('prefers the unit cost the source states, as the backend does', () => {
		expect(prum({ ...snapshot.accounts[0].lines![0], unit_cost: 38 })).toBe(38);
	});

	it('accepts any source: the backend knows which exist', () => {
		const other = { ...snapshot, source: 'another' };
		expect(decode(`#${encodeURIComponent(JSON.stringify(other))}`).source).toBe('another');
	});

	it('describes the reading without an amount', () => {
		const report = shape(snapshot);
		expect(report).toContain('"Afer Actions Monde C/D": quantity=yes');
		expect(report).toContain('invested=yes');
		expect(report).not.toMatch(/12345|200|160/);
	});
});
