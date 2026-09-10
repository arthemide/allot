/**
 * The demo store, end to end.
 *
 * Not the maths - that is the fixture in simulate.test.ts - but the wiring:
 * the sample portfolio a visitor lands on, a transaction going in and out,
 * a CSV replacing the sample, and the reset.
 */
import { describe, expect, it } from 'vitest';

import { refresh } from '$lib/state/refresh.svelte';
import { demoBackend, restartDemo, startDemo } from './demo';

describe('the demo backend', () => {
	it('lands on a full portfolio', async () => {
		startDemo();
		const positions = await demoBackend.getAssets();
		expect(positions).toHaveLength(5);
		const world = positions.find((p) => p.symbol === 'IE00B4L5Y983')!;
		// 42 opening units at 88.4 plus three buys.
		expect(world.quantity).toBeCloseTo(52);
		expect(world.prum).toBeGreaterThan(85);
		expect(world.market_value).toBeCloseTo(52 * 96.2);
		const summary = await demoBackend.getSummary();
		expect(summary.envelopes.map((e) => e.envelope)).toEqual(['CTO', 'PEA']);
		expect(summary.invested).toBeGreaterThan(0);
		const chart = await demoBackend.getChart('IE00B4L5Y983');
		expect(chart.transactions).toHaveLength(3);
		expect(chart.prum.length).toBeGreaterThan(3);
		const note = await demoBackend.getNote();
		expect(note).toContain('PEA');
		const envelopes = await demoBackend.getEnvelopes();
		expect(envelopes.map((e) => e.name)).toEqual(['PEA', 'CTO']);
	});

	it('takes a transaction and gives it back', async () => {
		startDemo();
		const before = (await demoBackend.getAsset('FR0010315770')).quantity;
		const tx = await demoBackend.addTransaction({
			symbol: 'FR0010315770',
			date: '2026-01-05',
			side: 'buy',
			quantity: 10,
			unit_price: 25,
			fees: 1
		});
		expect((await demoBackend.getAsset('FR0010315770')).quantity).toBeCloseTo(before + 10);
		await demoBackend.deleteTransaction(tx.id);
		expect((await demoBackend.getAsset('FR0010315770')).quantity).toBeCloseTo(before);
	});

	it('reads a CSV into an envelope', async () => {
		startDemo();
		const report = await demoBackend.importCsv('AV', 'name;isin;quantity;buyingPrice;lastPrice\nFonds euro;FR0000000001;10;100;110\n');
		expect(report.imported).toHaveLength(1);
		expect((await demoBackend.getEnvelopes()).map((e) => e.name)).toContain('AV');
		expect((await demoBackend.getAsset('FR0000000001')).envelope).toBe('AV');
	});

	it('starts over from whatever the visitor did to it', async () => {
		startDemo();
		await demoBackend.deleteAsset('FR0010315770');
		await demoBackend.addTransaction({
			symbol: 'IE00B4L5Y983',
			date: '2026-02-01',
			side: 'buy',
			quantity: 99,
			unit_price: 1,
			fees: 0
		});
		await demoBackend.setEnvelopeAmount('PEA', 4242);
		await demoBackend.importCsv('AV', 'name;isin;quantity;buyingPrice\nX;FR0000000002;1;1\n');

		const before = refresh.tick;
		restartDemo();

		const positions = await demoBackend.getAssets();
		expect(positions).toHaveLength(5);
		expect(positions.map((p) => p.symbol)).toContain('FR0010315770');
		expect((await demoBackend.getAsset('IE00B4L5Y983')).quantity).toBeCloseTo(52);
		expect((await demoBackend.getEnvelopes()).map((e) => e.name)).toEqual(['PEA', 'CTO']);
		expect((await demoBackend.getEnvelopes())[0].monthly_amount).toBe(400);
		// The page only re-reads because this moved.
		expect(refresh.tick).toBe(before + 1);
	});
});
