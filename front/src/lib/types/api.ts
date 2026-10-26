export interface Position {
	symbol: string;
	label: string;
	envelope: string;
	currency: string;
	weight: number;
	by_amount: boolean;
	base_quantity: number;
	base_prum: number | null;
	quantity: number;
	prum: number;
	invested: number;
	price: number | null;
	market_value: number | null;
	gain: number | null;
	gain_percent: number | null;
}

export interface Transaction {
	id: number;
	date: string;
	side: 'buy' | 'sell';
	quantity: number;
	unit_price: number;
	fees: number;
}

export interface PricePoint {
	date: string;
	price: number;
}

export interface PrumPoint {
	date: string;
	prum: number;
}

export interface Chart {
	symbol: string;
	currency: string;
	prices: PricePoint[];
	transactions: Transaction[];
	prum: PrumPoint[];
}

export interface NewTransaction {
	symbol: string;
	date: string;
	side: 'buy' | 'sell';
	quantity: number;
	unit_price: number;
	fees: number;
}

export interface SummaryAsset {
	symbol: string;
	label: string;
	currency: string;
	invested: number;
	market_value: number;
	gain: number;
	gain_percent: number | null;
}

export interface SummaryEnvelope {
	envelope: string;
	invested: number;
	market_value: number;
	gain: number;
	gain_percent: number | null;
	assets: SummaryAsset[];
}

export interface Summary {
	currency: string;
	eur_usd_rate: number | null;
	invested: number;
	market_value: number;
	gain: number;
	gain_percent: number | null;
	envelopes: SummaryEnvelope[];
}


export interface SearchHit {
	symbol: string;
	label: string;
	exchange: string;
	type: string;
	currency: string | null;
	price: number | null;
}

export interface Envelope {
	name: string;
	monthly_amount: number;
	/** Only set when the envelope tracks its cash; null otherwise. */
	started_on: string | null;
	opening_cash: number | null;
	available: number | null;
}

/** Where a strategy starts, or where it is recalibrated against a statement. */
export interface EnvelopeStart {
	started_on: string;
	opening_cash: number;
}

/** The address a calendar subscribes to, and whether it carries a token. */
export interface FeedUrl {
	url: string;
	token: boolean;
}

export interface NewAsset {
	symbol: string;
	label: string;
	envelope: string;
	currency: string;
	weight: number;
	by_amount?: boolean;
}

export interface AssetUpdate {
	label: string;
	envelope: string;
	weight: number;
	by_amount: boolean;
}

export interface ImportedLine {
	symbol: string;
	/** Null for a line mapped to its ticker by hand. */
	isin: string | null;
	label: string;
	quantity: number;
	prum: number;
}

/** A broker line no ticker in its currency answers to; nothing was written. */
export interface UnresolvedLine {
	/** Null for a line the broker does not tag. */
	isin: string | null;
	name: string;
}

/** An imported asset that already lived in another envelope. */
export interface ElsewhereLine {
	symbol: string;
	isin: string | null;
	label: string;
	envelope: string;
}

/** A bank line the recorded trades cannot be reconciled with; left as it was. */
export interface ConflictLine {
	symbol: string;
	label: string;
	bank_quantity: number;
	tracked_quantity: number;
}

export interface ImportReport {
	imported: ImportedLine[];
	unresolved: UnresolvedLine[];
	elsewhere: ElsewhereLine[];
	/** Only a bank sync reconciles against the recorded trades. */
	conflicts?: ConflictLine[];
	total: number;
}

/** A bank account no envelope was chosen for yet. */
export interface AccountChoice {
	account: string;
	lines: number;
	/** An existing envelope of the same name, offered as the default. */
	envelope: string | null;
}

/** Where an interactive bank login stands, and the import once it is through. */
export interface ConnectorStatus {
	session_id: string;
	status: 'otp' | 'app_validation' | 'accounts' | 'done';
	prompt: string;
	accounts: AccountChoice[];
	report: ImportReport | null;
}

/** Whether this instance asks for a password, and whether we gave it one. */
export type Session = {
	required: boolean;
	authenticated: boolean;
};
