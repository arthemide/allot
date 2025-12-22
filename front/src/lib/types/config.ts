export interface Stock {
	id?: string;
	symbol: string;
	parts_number: number;
	prum: number;
	current_repartition: number;
	target_repartition: number;
	arbitration_threshold: number;
	threshold_to_alert: number;
}

export interface FundConfig {
	id?: string;
	fund_name: string;
	stocks: Stock[];
	created_at?: string;
	updated_at?: string;
}

export interface StockFormData {
	symbol: string;
	parts_number: string;
	prum: string;
	current_repartition: string;
	target_repartition: string;
	arbitration_threshold: string;
	threshold_to_alert: string;
}
