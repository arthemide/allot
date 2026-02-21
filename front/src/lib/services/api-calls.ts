import type { AssetTransaction, FundConfig, Stock } from '$lib/types/config';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const configApi = {
	// Get all fund configurations
	async getAllConfigs(): Promise<FundConfig[]> {
		const response = await fetch(`${API_BASE_URL}/funds`);
		if (!response.ok) {
			throw new Error(`Failed to fetch configs: ${response.statusText}`);
		}
		return response.json();
	},

	// Get a single fund configuration by ID
	async getConfig(id: string): Promise<FundConfig | null> {
		const response = await fetch(`${API_BASE_URL}/funds/${id}`);
		if (response.status === 404) {
			return null;
		}
		if (!response.ok) {
			throw new Error(`Failed to fetch config: ${response.statusText}`);
		}
		return response.json();
	},

	// Create a new fund configuration
	async createConfig(fundName: string): Promise<FundConfig> {
		const response = await fetch(`${API_BASE_URL}/funds`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ fund_name: fundName, stocks: [] })
		});
		if (!response.ok) {
			throw new Error(`Failed to create config: ${response.statusText}`);
		}
		return response.json();
	},

	// Update an existing fund configuration
	async updateConfig(id: string, updates: Partial<FundConfig>): Promise<FundConfig | null> {
		const response = await fetch(`${API_BASE_URL}/funds/${id}`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updates)
		});
		if (response.status === 404) {
			return null;
		}
		if (!response.ok) {
			throw new Error(`Failed to update config: ${response.statusText}`);
		}
		return response.json();
	},

	// Delete a fund configuration
	async deleteConfig(id: string): Promise<boolean> {
		const response = await fetch(`${API_BASE_URL}/funds/${id}`, {
			method: 'DELETE'
		});
		if (response.status === 404) {
			return false;
		}
		if (!response.ok) {
			throw new Error(`Failed to delete config: ${response.statusText}`);
		}
		return true;
	},

	// Add a stock to a fund configuration
	async addStock(fundId: string, stock: Omit<Stock, 'id'>): Promise<FundConfig | null> {
		const response = await fetch(`${API_BASE_URL}/funds/${fundId}/stocks`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(stock)
		});
		if (response.status === 404) {
			return null;
		}
		if (!response.ok) {
			throw new Error(`Failed to add stock: ${response.statusText}`);
		}
		return response.json();
	},

	// Update a stock in a fund configuration
	async updateStock(fundId: string, stockId: string, updates: Partial<Stock>): Promise<FundConfig | null> {
		const response = await fetch(`${API_BASE_URL}/funds/${fundId}/stocks/${stockId}`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updates)
		});
		if (response.status === 404) {
			return null;
		}
		if (!response.ok) {
			throw new Error(`Failed to update stock: ${response.statusText}`);
		}
		return response.json();
	},

	// Remove a stock from a fund configuration
	async removeStock(fundId: string, stockId: string): Promise<FundConfig | null> {
		const response = await fetch(`${API_BASE_URL}/funds/${fundId}/stocks/${stockId}`, {
			method: 'DELETE'
		});
		if (response.status === 404) {
			return null;
		}
		if (!response.ok) {
			throw new Error(`Failed to remove stock: ${response.statusText}`);
		}
		return response.json();
	}
};

export const stockApi = {
	async getPriceHistory(
		symbol: string,
		start: string,
		end: string
	): Promise<{ date: string; price: number }[]> {
		const url = new URL(`${API_BASE_URL}/stocks/price-history`);
		url.searchParams.set('symbol', symbol);
		url.searchParams.set('start', start);
		url.searchParams.set('end', end);
		const response = await fetch(url.toString());
		if (!response.ok) {
			return [];
		}
		return response.json();
	}
};

export const transactionApi = {
	async getAll(params?: {
		fund_id?: string;
		asset_id?: string;
		limit?: number;
	}): Promise<AssetTransaction[]> {
		const url = new URL(`${API_BASE_URL}/transactions`);
		if (params?.fund_id) url.searchParams.set('fund_id', params.fund_id);
		if (params?.asset_id) url.searchParams.set('asset_id', params.asset_id);
		if (params?.limit !== undefined) url.searchParams.set('limit', String(params.limit));

		const response = await fetch(url.toString());
		if (!response.ok) {
			throw new Error(`Failed to fetch transactions: ${response.statusText}`);
		}
		return response.json();
	}
};

