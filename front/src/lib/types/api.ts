export interface Position {
	symbol: string;
	label: string;
	envelope: string;
	currency: string;
	price_source: 'yfinance' | 'manual';
	quantity: number | null;
	prum: number | null;
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
