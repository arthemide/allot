import type { Chart, NewTransaction, Position, Transaction } from '$lib/types/api';

// Empty in production: app.py serves the front from the same origin.
const BASE = import.meta.env.DEV ? 'http://localhost:8000' : '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${BASE}${path}`, {
		headers: { 'Content-Type': 'application/json' },
		...init
	});
	if (!response.ok) {
		throw new Error(`${init?.method ?? 'GET'} ${path} failed: ${response.status}`);
	}
	return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const getAssets = () => request<Position[]>('/assets');

export const getAsset = (symbol: string) =>
	request<Position>(`/assets/${encodeURIComponent(symbol)}`);

export const getChart = (symbol: string) =>
	request<Chart>(`/assets/${encodeURIComponent(symbol)}/chart`);

export const getTransactions = (symbol: string) =>
	request<Transaction[]>(`/transactions?symbol=${encodeURIComponent(symbol)}`);

export const addTransaction = (transaction: NewTransaction) =>
	request<Transaction>('/transactions', {
		method: 'POST',
		body: JSON.stringify(transaction)
	});

export const deleteTransaction = (id: number) =>
	request<void>(`/transactions/${id}`, { method: 'DELETE' });

export const setManualValue = (symbol: string, value: number) =>
	request<Position>(`/assets/${encodeURIComponent(symbol)}/manual-value`, {
		method: 'PUT',
		body: JSON.stringify({ value })
	});



export async function getNote(): Promise<string> {
	const response = await fetch(`${BASE}/note`);
	if (!response.ok) throw new Error(`GET /note failed: ${response.status}`);
	return response.text();
}
