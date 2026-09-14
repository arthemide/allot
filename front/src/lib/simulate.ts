/**
 * The allocation, entirely in the browser.
 *
 * A faithful port of the pieces of `src/calc.py` the simulator needs, so a
 * visitor's CSV never leaves their machine. Only the euro-split path is
 * ported (the one an untracked envelope uses): the monthly amount is shared
 * across an envelope's assets, weighted and modulated by each one's gap to its
 * PRUM. Whole-share lots, cash tracking and projection stay server-side in the
 * app; they are not part of this taste-test.
 *
 * Kept deliberately small and pure so it stays in step with calc.py by
 * inspection. If calc.py's multiplier or renormalize change, change them here.
 */

// Mirror of calc.MODULATION_BAND / MULTIPLIER_* .
export const MODULATION_BAND = 0.1;
const MULTIPLIER_BELOW = 1.5;
const MULTIPLIER_ABOVE = 0.5;
const MULTIPLIER_NEUTRAL = 1;

export type Row = {
	isin: string;
	name: string;
	quantity: number;
	prum: number;
	price: number | null;
};

export type ParseResult = { rows: Row[]; broker: string } | { error: string };

export type EnvelopeInput = { name: string; monthly: number };
export type Assignment = { isin: string; envelope: string; weight: number };

export type PlanAsset = {
	symbol: string;
	isin: string;
	amount: number;
	multiplier: number;
	price: number | null;
	prum: number;
};
export type PlanEnvelope = { name: string; budget: number; assets: PlanAsset[] };

// --- CSV reading ---------------------------------------------------------

const ROLES: Record<string, string[]> = {
	identifier: ['isin', 'codeisin', 'symbol', 'symbole', 'ticker', 'mnemo', 'code'],
	quantity: ['quantity', 'quantite', 'qte', 'qty', 'nombredeparts', 'parts', 'shares'],
	cost: [
		'buyingprice',
		'pru',
		'prixderevient',
		'prixdachat',
		'prixmoyen',
		'averageprice',
		'prixunitairemoyen'
	],
	valuation: ['lastprice', 'amount', 'valuation', 'valorisation', 'cours', 'derniercours'],
	name: ['name', 'nom', 'label', 'libelle', 'designation', 'intitule']
};
const MOVEMENTS = ['dateop', 'label', 'amount'];

function strip(header: string): string {
	return header
		.toLowerCase()
		.normalize('NFD')
		.replace(/[̀-ͯ]/g, '')
		.replace(/[^a-z0-9]/g, '');
}

function roleOf(header: string): string | null {
	const key = strip(header);
	if (!key) return null;
	for (const [role, names] of Object.entries(ROLES)) if (names.includes(key)) return role;
	for (const [role, names] of Object.entries(ROLES))
		if (names.some((n) => n.length >= 4 && key.includes(n))) return role;
	return null;
}

function detectDelimiter(firstLine: string): string {
	const counts: Record<string, number> = { ';': 0, ',': 0, '\t': 0, '|': 0 };
	let quoted = false;
	for (const c of firstLine) {
		if (c === '"') quoted = !quoted;
		else if (!quoted && c in counts) counts[c]++;
	}
	let best = ';';
	for (const d of Object.keys(counts)) if (counts[d] > counts[best]) best = d;
	return counts[best] ? best : ';';
}

// A proper split: quoted fields may hold the delimiter.
function splitRow(line: string, delimiter: string): string[] {
	const cells: string[] = [];
	let field = '';
	let quoted = false;
	for (let i = 0; i < line.length; i++) {
		const c = line[i];
		if (quoted) {
			if (c === '"') {
				if (line[i + 1] === '"') {
					field += '"';
					i++;
				} else quoted = false;
			} else field += c;
		} else if (c === '"') quoted = true;
		else if (c === delimiter) {
			cells.push(field);
			field = '';
		} else field += c;
	}
	cells.push(field);
	return cells.map((c) => c.trim());
}

function toNumber(text: string | undefined): number | null {
	if (text == null) return null;
	let cleaned = text.replace(/[\s  ]/g, '');
	cleaned = cleaned.replace(/[^0-9,.-]/g, '');
	if (!cleaned) return null;
	// A comma is the decimal mark either way: "1.234,56" or "1234,56".
	if (cleaned.includes(',')) cleaned = cleaned.replace(/\./g, '').replace(',', '.');
	const value = parseFloat(cleaned);
	return Number.isNaN(value) ? null : value;
}

export function parsePortfolioCsv(text: string): ParseResult {
	const clean = text.replace(/^﻿/, '');
	const firstLine = clean.split(/\r?\n/)[0] ?? '';
	if (!firstLine.trim()) return { error: 'Fichier vide.' };

	const delimiter = detectDelimiter(firstLine);
	const lines = clean.split(/\r?\n/).filter((l) => l.trim());
	const headers = splitRow(lines[0], delimiter);
	const keys = headers.map(strip);
	const broker =
		keys.includes('isin') && keys.includes('quantity') && keys.includes('buyingprice')
			? 'BoursoBank'
			: 'inconnu';

	const column: Record<string, number> = {};
	headers.forEach((h, i) => {
		const role = roleOf(h);
		if (role && !(role in column)) column[role] = i;
	});

	for (const required of ['identifier', 'quantity', 'cost']) {
		if (!(required in column)) {
			if (MOVEMENTS.every((k) => keys.includes(k)))
				return {
					error:
						"C'est un export de mouvements (date, libellé, montant). Exporte le portefeuille : il porte la quantité et le prix de revient."
				};
			return { error: `Colonne manquante : ${required}.` };
		}
	}

	const rows: Row[] = [];
	for (let i = 1; i < lines.length; i++) {
		const cells = splitRow(lines[i], delimiter);
		const at = (role: string) => cells[column[role]];
		const isin = (at('identifier') ?? '').toUpperCase();
		if (!isin) continue;
		const quantity = toNumber(at('quantity'));
		const prum = toNumber(at('cost'));
		if (quantity == null || quantity <= 0) return { error: `Ligne ${i + 1} : quantité invalide.` };
		if (prum == null || prum <= 0) return { error: `Ligne ${i + 1} : prix de revient invalide.` };
		const price = 'valuation' in column ? toNumber(at('valuation')) : null;
		rows.push({
			isin,
			name: (column.name != null ? at('name') : '') || isin,
			quantity,
			prum,
			price: price && price > 0 ? price : null
		});
	}
	return { rows, broker };
}

// --- Allocation (port of calc.multiplier / calc.renormalize) -------------

export function multiplier(price: number | null, prum: number): number {
	if (!price || prum <= 0) return MULTIPLIER_NEUTRAL;
	const gap = (price - prum) / prum;
	if (gap < -MODULATION_BAND) return MULTIPLIER_BELOW;
	if (gap > MODULATION_BAND) return MULTIPLIER_ABOVE;
	return MULTIPLIER_NEUTRAL;
}

function renormalize(budget: number, weighted: [number, number][]): number[] {
	const products = weighted.map(([weight, mult]) => weight * mult);
	const total = products.reduce((a, b) => a + b, 0);
	if (total === 0) return products.map(() => 0);
	return products.map((p) => (budget * p) / total);
}

export function allocate(
	rows: Row[],
	envelopes: EnvelopeInput[],
	assignments: Assignment[]
): PlanEnvelope[] {
	const byIsin = new Map(rows.map((r) => [r.isin, r]));
	return envelopes
		.filter((e) => e.name.trim())
		.map((envelope) => {
			const members = assignments
				.filter((a) => a.envelope === envelope.name && byIsin.has(a.isin))
				.map((a) => ({ assignment: a, row: byIsin.get(a.isin)! }));
			const amounts = renormalize(
				envelope.monthly,
				members.map((m) => [m.assignment.weight, multiplier(m.row.price, m.row.prum)])
			);
			return {
				name: envelope.name,
				budget: envelope.monthly,
				assets: members.map((m, i) => ({
					symbol: m.row.name,
					isin: m.row.isin,
					amount: amounts[i],
					multiplier: multiplier(m.row.price, m.row.prum),
					price: m.row.price,
					prum: m.row.prum
				}))
			};
		});
}
