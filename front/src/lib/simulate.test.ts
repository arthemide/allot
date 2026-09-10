/**
 * The other half of the contract with `src/calc.py`.
 *
 * These cases live in tests/fixtures/calc_cases.json and are replayed by
 * tests/test_calc.py too. If the app's maths moves, the Python side fails
 * first; once the fixture is updated, this file fails until the port here
 * catches up. Nothing else keeps the two in step.
 */
import { describe, expect, it } from 'vitest';

import cases from '../../../tests/fixtures/calc_cases.json';
import { allocate, gainPercent, multiplier, position, summarize, type Trade } from './simulate';

const close = (value: number | null, expected: number | null) => {
	if (expected === null) expect(value).toBeNull();
	else expect(value).toBeCloseTo(expected, 9);
};

describe('position', () => {
	for (const c of cases.position) {
		it(c.name, () => {
			const result = position(c.trades as Trade[], c.base_quantity, c.base_prum);
			close(result.quantity, c.expected.quantity);
			close(result.prum, c.expected.prum);
			close(result.invested, c.expected.invested);

			const marketValue = c.price === null ? null : result.quantity * c.price;
			close(marketValue, c.expected.market_value);
			close(
				marketValue === null ? null : marketValue - result.invested,
				c.expected.gain
			);
			close(
				marketValue === null ? null : gainPercent(result.invested, marketValue),
				c.expected.gain_percent
			);
		});
	}
});

describe('multiplier', () => {
	for (const c of cases.multiplier) {
		it(c.name, () => close(multiplier(c.price, c.prum), c.expected));
	}

	it('leaves an unquoted asset alone', () => {
		// The browser has no price source of its own: a line without a quote
		// must not be read as "far below the cost basis".
		expect(multiplier(null, 100)).toBe(1);
	});
});

// renormalize is not exported: allocate is the only way in, so drive it with
// one envelope holding one line per weight/multiplier pair.
describe('renormalize, through allocate', () => {
	for (const c of cases.renormalize) {
		it(c.name, () => {
			const rows = c.weighted.map(([, mult]: number[], i: number) => ({
				isin: `ISIN${i}`,
				name: `Line ${i}`,
				quantity: 1,
				prum: 100,
				// The multiplier the fixture asks for, expressed as a price.
				price: mult === 1.5 ? 80 : mult === 0.5 ? 120 : 100
			}));
			const plan = allocate(
				rows,
				[{ name: 'PEA', monthly: c.budget }],
				c.weighted.map(([weight]: number[], i: number) => ({
					isin: `ISIN${i}`,
					envelope: 'PEA',
					weight
				}))
			);
			expect(plan[0].assets.map((a) => a.amount)).toHaveLength(c.expected.length);
			plan[0].assets.forEach((asset, i) => close(asset.amount, c.expected[i]));
		});
	}
});

describe('summarize', () => {
	for (const c of cases.summary) {
		it(c.name, () => {
			const result = summarize(
				c.positions.map((p: Record<string, unknown>) => ({ ...p }) as never)
			);
			close(result.invested, c.expected.invested);
			close(result.market_value, c.expected.market_value);
			close(result.gain, c.expected.gain);
			close(result.gain_percent, c.expected.gain_percent);
			expect(result.envelopes.map((e) => e.envelope)).toEqual(
				c.expected.envelopes.map((e: { envelope: string }) => e.envelope)
			);
			result.envelopes.forEach((got, i) => {
				const want = c.expected.envelopes[i];
				close(got.invested, want.invested);
				close(got.market_value, want.market_value);
				close(got.gain, want.gain);
				close(got.gain_percent, want.gain_percent);
			});
		});
	}
});
