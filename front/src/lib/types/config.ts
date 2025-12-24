export interface Stock {
	id?: string;
	name: string | null;
	symbol: string;
	shares_number: number;
	cost: number;
	today_price?: number;
	prum?: number;
	market_value?: number;
	gain_loss?: number;
	gain_loss_percentage?: number;
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
	total_cost?: number;
	total_market_value?: number;
	total_gain_loss?: number;
	average_gain_loss_percentage?: number;
}

export interface StockFormData {
	symbol: string;
	shares_number: string;
	cost: string;
	current_repartition: string;
	target_repartition: string;
	arbitration_threshold: string;
	threshold_to_alert: string;
}
