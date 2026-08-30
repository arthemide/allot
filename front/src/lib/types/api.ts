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
}

export interface NewAsset {
	symbol: string;
	label: string;
	envelope: string;
	currency: string;
	weight: number;
}

/** Whether this instance asks for a password, and whether we gave it one. */
export type Session = {
	required: boolean;
	authenticated: boolean;
};
