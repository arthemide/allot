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
	actual_quantity: number | null;
	quantity_gap: number | null;
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

export interface BuySimulation {
	amount: number;
	fees: number;
	quantity: number;
	new_prum: number;
}

export interface TargetSimulation {
	target_prum: number;
	reachable: boolean;
	reason: string | null;
	quantity: number | null;
	amount: number | null;
}

export interface Simulation {
	symbol: string;
	currency: string;
	price: number;
	quantity: number;
	prum: number;
	buy: BuySimulation | null;
	target: TargetSimulation | null;
}
