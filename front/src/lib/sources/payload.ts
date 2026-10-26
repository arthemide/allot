/**
 * What Allot does with what a source's bookmarklet hands it.
 *
 * Which sources exist is the backend's to say: the shape is checked here, the
 * source name when the reading is sent.
 */
import type { SourceAccount, SourceLine, SourceSnapshot } from './bookmarklet.js';

const isNumber = (value: unknown) =>
	value === null || value === undefined || typeof value === 'number';
const isText = (value: unknown) => typeof value === 'string';

function isLine(value: unknown): value is SourceLine {
	const line = value as SourceLine;
	return (
		typeof line === 'object' &&
		line !== null &&
		isText(line.label) &&
		isNumber(line.quantity) &&
		isNumber(line.unit_cost) &&
		isNumber(line.invested) &&
		isNumber(line.unit_value) &&
		isNumber(line.valuation)
	);
}

function isAccount(value: unknown): value is SourceAccount {
	const account = value as SourceAccount;
	return (
		typeof account === 'object' &&
		account !== null &&
		isText(account.label) &&
		isNumber(account.balance) &&
		(account.lines === undefined ||
			(Array.isArray(account.lines) && account.lines.every(isLine)))
	);
}

/** The snapshot carried by a URL fragment, or why it is not one. */
export function decode(fragment: string): SourceSnapshot {
	const raw = fragment.startsWith('#') ? fragment.slice(1) : fragment;
	let value: unknown;
	try {
		value = JSON.parse(decodeURIComponent(raw));
	} catch {
		throw new Error('The link does not carry a reading. Click the bookmark again.');
	}
	const snapshot = value as SourceSnapshot;
	if (
		typeof snapshot !== 'object' ||
		snapshot === null ||
		!isText(snapshot.source) ||
		snapshot.source === '' ||
		typeof snapshot.version !== 'number' ||
		!Array.isArray(snapshot.accounts) ||
		!snapshot.accounts.every(isAccount)
	) {
		throw new Error(
			'This reading has an unexpected shape. Update the bookmark from Allot and try again.'
		);
	}
	return snapshot;
}

/**
 * The PRUM of a line, as the backend derives it (source_sync.rows_from_snapshot):
 * the unit cost the source states, else what was paid in per unit.
 */
export function prum(line: SourceLine): number | null {
	if (line.unit_cost !== null && line.unit_cost !== undefined) return line.unit_cost;
	if (line.invested !== null && line.invested !== undefined && line.quantity) {
		return line.invested / line.quantity;
	}
	return null;
}

/** The structure of a reading without a single amount, to paste in a bug report. */
export function shape(snapshot: SourceSnapshot): string {
	const out = [`Reading v${snapshot.version}, ${snapshot.accounts.length} account(s)`];
	for (const account of snapshot.accounts) {
		out.push('', `account "${account.label}": lines=${(account.lines ?? []).length}`);
		for (const line of account.lines ?? []) {
			const has = (value: unknown) => (value === null || value === undefined ? 'no' : 'yes');
			out.push(`  "${line.label}": quantity=${has(line.quantity)} invested=${has(line.invested)}`);
		}
	}
	return out.join('\n');
}
