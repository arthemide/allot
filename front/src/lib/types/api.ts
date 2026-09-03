export interface Position {
	symbol: string;
	label: string;
	envelope: string;
	currency: string;
	weight: number;
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
}

export interface AssetUpdate {
	label: string;
	envelope: string;
	weight: number;
}

/** Whether this instance asks for a password, and whether we gave it one. */
export type Session = {
	required: boolean;
	authenticated: boolean;
};
