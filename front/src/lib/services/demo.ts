/**
 * The whole backend, in the tab.
 *
 * The /demo page mounts the real app; only this file stands in for the
 * server, so a visitor's portfolio never leaves their machine. It holds the
 * state and answers the same calls, but computes nothing itself: every
 * formula lives in `$lib/simulate`, the single mirror of `src/calc.py`.
 *
 * A refresh lays the sample portfolio out again: nothing here persists, which
 * is the point.
 */
import type {
	AssetUpdate,
	Chart,
	Envelope,
	EnvelopeStart,
	NewAsset,
	NewTransaction,
	Position,
	PrumPoint,
	Summary,
	Transaction
} from '$lib/types/api';
import type * as http from './http';
import {
	allocate,
	gainPercent,
	parsePortfolioCsv,
	position as recompute,
	summarize,
	type Row,
	type Trade
} from '$lib/simulate';
import { refresh } from '$lib/state/refresh.svelte';

/** A transaction plus the asset it belongs to, which the API infers from its route. */
type StoredTransaction = Transaction & { symbol: string };

/** What an asset carries before quantity and PRUM are recomputed from it. */
type Asset = {
	symbol: string;
	label: string;
	envelope: string;
	currency: string;
	weight: number;
	base_quantity: number;
	base_prum: number | null;
	price: number | null;
};

let assets: Asset[] = [];
let envelopes: Envelope[] = [];
let transactions: StoredTransaction[] = [];
let nextId = 1;

/** The API is a network away; the demo answers instantly, which reads as broken. */
const answer = <T>(value: T): Promise<T> => Promise.resolve(structuredClone(value));

const fail = (message: string) => Promise.reject(new Error(message));

function assetOf(symbol: string): Asset {
	const asset = assets.find((a) => a.symbol === symbol);
	if (!asset) throw new Error(`Unknown asset: ${symbol}`);
	return asset;
}

const tradesOf = (symbol: string): Trade[] =>
	transactions
		.filter((t) => t.symbol === symbol)
		.sort((a, b) => a.date.localeCompare(b.date))
		.map((t) => ({ side: t.side, quantity: t.quantity, unit_price: t.unit_price, fees: t.fees }));

function positionOf(asset: Asset): Position {
	const result = recompute(tradesOf(asset.symbol), asset.base_quantity, asset.base_prum);
	const marketValue = asset.price === null ? null : result.quantity * asset.price;
	return {
		symbol: asset.symbol,
		label: asset.label,
		envelope: asset.envelope,
		currency: asset.currency,
		weight: asset.weight,
		base_quantity: asset.base_quantity,
		base_prum: asset.base_prum,
		quantity: result.quantity,
		prum: result.prum,
		invested: result.invested,
		price: asset.price,
		market_value: marketValue,
		gain: marketValue === null ? null : marketValue - result.invested,
		gain_percent: marketValue === null ? null : gainPercent(result.invested, marketValue)
	};
}

const positions = (): Position[] => assets.map(positionOf);

/**
 * A portfolio to land in.
 *
 * Invented figures on real trackers, spread so the app has something to say:
 * one line well below its cost basis (topped up), one well above (eased off),
 * the rest around it. The visitor replaces the lot with their own export from
 * the nav whenever they want.
 */
const SAMPLE: { asset: Asset; envelope: string }[] = [
	{
		envelope: 'PEA',
		asset: {
			symbol: 'IE00B4L5Y983',
			label: 'iShares Core MSCI World',
			envelope: 'PEA',
			currency: 'EUR',
			weight: 3,
			base_quantity: 42,
			base_prum: 88.4,
			price: 96.2
		}
	},
	{
		envelope: 'PEA',
		asset: {
			symbol: 'FR0010315770',
			label: 'Lyxor MSCI Europe',
			envelope: 'PEA',
			currency: 'EUR',
			weight: 1,
			base_quantity: 60,
			base_prum: 27.9,
			// Below the cost basis by more than 10%: the plan tops it up.
			price: 24.1
		}
	},
	{
		envelope: 'PEA',
		asset: {
			symbol: 'FR0011871128',
			label: 'Amundi S&P 500',
			envelope: 'PEA',
			currency: 'EUR',
			weight: 2,
			base_quantity: 25,
			base_prum: 36.5,
			// Well above: the plan eases off.
			price: 44.8
		}
	},
	{
		envelope: 'CTO',
		asset: {
			symbol: 'IE00BFNM3P36',
			label: 'Amundi MSCI Emerging Markets',
			envelope: 'CTO',
			currency: 'EUR',
			weight: 1,
			base_quantity: 30,
			base_prum: 21.3,
			price: 22.05
		}
	},
	{
		envelope: 'CTO',
		asset: {
			symbol: 'IE00BYZK4552',
			label: 'iShares Automation & Robotics',
			envelope: 'CTO',
			currency: 'EUR',
			weight: 1,
			base_quantity: 18,
			base_prum: 13.75,
			price: 15.9
		}
	}
];

/** A month of buys on the first line, so a chart and a table have something to show. */
const SAMPLE_TRANSACTIONS: Omit<StoredTransaction, 'id'>[] = [
	{
		symbol: 'IE00B4L5Y983',
		date: monthsAgo(6),
		side: 'buy',
		quantity: 4,
		unit_price: 84.1,
		fees: 1.5
	},
	{
		symbol: 'IE00B4L5Y983',
		date: monthsAgo(3),
		side: 'buy',
		quantity: 3,
		unit_price: 91.7,
		fees: 1.5
	},
	{
		symbol: 'IE00B4L5Y983',
		date: monthsAgo(1),
		side: 'buy',
		quantity: 3,
		unit_price: 95.4,
		fees: 1.5
	}
];

function monthsAgo(count: number): string {
	const date = new Date();
	date.setMonth(date.getMonth() - count);
	return date.toISOString().slice(0, 10);
}

/** Lay out the sample portfolio. Called on arrival, and again on "Start over". */
export function startDemo() {
	assets = SAMPLE.map(({ asset }) => ({ ...asset }));
	envelopes = [
		{ name: 'PEA', monthly_amount: 400, started_on: null, opening_cash: null, available: null },
		{ name: 'CTO', monthly_amount: 150, started_on: null, opening_cash: null, available: null }
	];
	transactions = SAMPLE_TRANSACTIONS.map((t) => ({ ...t, id: nextId++ }));
}

/** Lay it out again and tell the app to re-read. */
export function restartDemo() {
	nextId = 1;
	startDemo();
	refresh.bump();
}

/** The monthly note, short form: what to buy, by envelope. */
function renderNote(): string {
	const rows: Row[] = assets.map((a) => ({
		isin: a.symbol,
		name: a.label,
		quantity: a.base_quantity,
		prum: positionOf(a).prum,
		price: a.price
	}));
	const plan = allocate(
		rows,
		envelopes.map((e) => ({ name: e.name, monthly: e.monthly_amount })),
		assets.map((a) => ({ isin: a.symbol, envelope: a.envelope, weight: a.weight }))
	);
	const month = new Date().toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
	const lines = [`Allot - ${month}`, ''];
	for (const envelope of plan) {
		lines.push(`${envelope.name} - ${Math.round(envelope.budget)} EUR`);
		const buying = envelope.assets.filter((a) => a.amount > 0);
		if (!buying.length) lines.push('  Nothing to invest: no weighted asset.');
		for (const asset of buying) lines.push(`  [ ] ${asset.symbol} - ${asset.amount.toFixed(2)} EUR`);
		lines.push('');
	}
	lines.push('Simulator: this note is computed in your browser and saved nowhere.');
	return lines.join('\n');
}

export const demoBackend = {
	getAssets: () => answer(positions()),

	getSummary: () => answer(summarize(positions()) as Summary),

	getAsset: (symbol: string) => answer(positionOf(assetOf(symbol))),

	getChart: (symbol: string, _window = 'tx') => {
		const asset = assetOf(symbol);
		const own = transactions
			.filter((t) => t.symbol === symbol)
			.sort((a, b) => a.date.localeCompare(b.date));
		// No price history to be had in the browser: the chart starts empty and
		// fills with the PRUM the visitor's own transactions draw.
		const prum: PrumPoint[] = [];
		if (asset.base_prum && own.length)
			prum.push({ date: own[0].date, prum: asset.base_prum });
		const running: Trade[] = [];
		for (const t of own) {
			running.push({ side: t.side, quantity: t.quantity, unit_price: t.unit_price, fees: t.fees });
			prum.push({
				date: t.date,
				prum: recompute(running, asset.base_quantity, asset.base_prum).prum
			});
		}
		const chart: Chart = {
			symbol,
			currency: asset.currency,
			prices: [],
			transactions: own.map(({ symbol: _s, ...rest }) => rest),
			prum
		};
		return answer(chart);
	},

	setOpeningPosition: (symbol: string, body: { quantity: number; invested: number | null }) => {
		const asset = assetOf(symbol);
		asset.base_quantity = body.quantity;
		asset.base_prum = body.invested === null || !body.quantity ? null : body.invested / body.quantity;
		return answer(positionOf(asset));
	},

	getTransactions: (symbol: string) =>
		answer(
			transactions.filter((t) => t.symbol === symbol).map(({ symbol: _s, ...rest }) => rest)
		),

	addTransaction: (transaction: NewTransaction) => {
		const { symbol, ...rest } = transaction;
		const stored: StoredTransaction = { id: nextId++, symbol, ...rest };
		transactions = [...transactions, stored];
		const { symbol: _s, ...row } = stored;
		return answer(row as Transaction);
	},

	deleteTransaction: (id: number) => {
		transactions = transactions.filter((t) => t.id !== id);
		return answer(undefined as void);
	},

	getNote: () => answer(renderNote()),

	// A calendar cannot subscribe to a page that holds nothing: the nav hides
	// this in the demo, and reaching it anyway should say why.
	getFeedUrl: () => fail('The calendar feed needs the real app.'),

	getSession: () => answer({ required: false, authenticated: true }),

	login: () => answer(undefined as void),

	searchTickers: () => fail('Ticker search needs the real app.'),

	createAsset: (asset: NewAsset) => {
		assets = [
			...assets,
			{ ...asset, base_quantity: 0, base_prum: null, price: null }
		];
		return answer(positionOf(assetOf(asset.symbol)));
	},

	importCsv: (envelope: string, csv: string) => {
		// The same reader the app runs server-side, here in the tab.
		const result = parsePortfolioCsv(csv);
		if ('error' in result) return fail(result.error);
		const name = envelope.trim().toUpperCase();
		if (!envelopes.some((e) => e.name === name))
			envelopes = [
				...envelopes,
				{ name, monthly_amount: 0, started_on: null, opening_cash: null, available: null }
			];

		const imported = [];
		const elsewhere = [];
		for (const row of result.rows) {
			const existing = assets.find((a) => a.symbol === row.isin);
			if (existing && existing.envelope !== name) {
				elsewhere.push({
					symbol: existing.symbol,
					isin: row.isin,
					label: existing.label,
					envelope: existing.envelope
				});
				continue;
			}
			const asset = existing ?? {
				symbol: row.isin,
				label: row.name,
				envelope: name,
				currency: 'EUR',
				weight: 1,
				base_quantity: 0,
				base_prum: null,
				price: null
			};
			// An imported line is a holding that predates transaction tracking.
			asset.base_quantity = row.quantity;
			asset.base_prum = row.prum;
			asset.price = row.price;
			if (!existing) assets = [...assets, asset];
			imported.push({
				symbol: asset.symbol,
				isin: row.isin,
				label: asset.label,
				quantity: row.quantity,
				prum: row.prum
			});
		}
		return answer({ imported, unresolved: [], elsewhere, total: result.rows.length });
	},

	updateAsset: (symbol: string, body: AssetUpdate) => {
		const asset = assetOf(symbol);
		asset.label = body.label;
		asset.envelope = body.envelope;
		asset.weight = body.weight;
		return answer(positionOf(asset));
	},

	deleteAsset: (symbol: string) => {
		assets = assets.filter((a) => a.symbol !== symbol);
		transactions = transactions.filter((t) => t.symbol !== symbol);
		return answer(undefined as void);
	},

	getEnvelopes: () => answer(envelopes),

	setEnvelopeAmount: (name: string, monthlyAmount: number) => {
		const envelope = envelopes.find((e) => e.name === name);
		if (!envelope) return fail(`Unknown envelope: ${name}`);
		envelope.monthly_amount = monthlyAmount;
		return answer(envelope);
	},

	setEnvelopeStart: (name: string, body: EnvelopeStart) => {
		const envelope = envelopes.find((e) => e.name === name);
		if (!envelope) return fail(`Unknown envelope: ${name}`);
		envelope.started_on = body.started_on;
		envelope.opening_cash = body.opening_cash;
		// The server drains this with the month's buys; nothing here spends it.
		envelope.available = body.opening_cash;
		return answer(envelope);
	},

	clearEnvelopeStart: (name: string) => {
		const envelope = envelopes.find((e) => e.name === name);
		if (!envelope) return fail(`Unknown envelope: ${name}`);
		envelope.started_on = null;
		envelope.opening_cash = null;
		envelope.available = null;
		return answer(envelope);
	}
	// The guard: an endpoint added to http.ts and forgotten here stops the build.
} satisfies typeof http;
