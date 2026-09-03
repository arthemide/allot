import { session } from '$lib/state/session.svelte';
import type {
	AssetUpdate,
	Chart,
	Envelope,
	EnvelopeStart,
	FeedUrl,
	NewAsset,
	NewTransaction,
	Position,
	SearchHit,
	Session,
	Summary,
	Transaction
} from '$lib/types/api';

// Empty in production: app.py serves the front from the same origin.
const BASE = import.meta.env.DEV ? 'http://localhost:8000' : '';

/** Surface what the API actually said, not just the status code. */
async function errorMessage(response: Response, path: string, method: string) {
	try {
		const body = await response.json();
		// FastAPI puts a plain string in `detail`, or a list of field errors
		// when the payload failed validation.
		if (typeof body.detail === 'string') return body.detail;
		if (Array.isArray(body.detail)) {
			return body.detail
				.map((issue: { loc?: unknown[]; msg?: string }) => {
					const field = issue.loc?.slice(1).join('.') ?? '';
					return field ? `${field}: ${issue.msg}` : issue.msg;
				})
				.join(', ');
		}
	} catch {
		// No JSON body: fall through to the generic message.
	}
	return `${method} ${path} failed (${response.status})`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${BASE}${path}`, {
		headers: { 'Content-Type': 'application/json' },
		// The dev server is cross-origin (:5173 -> :8000), where the browser
		// will not send the session cookie on its own.
		credentials: 'include',
		...init
	});
	// A 401 from /login itself is a wrong password, and has to reach the form.
	if (response.status === 401 && path !== '/login') {
		session.expired();
		throw new Error('Session expired.');
	}
	if (!response.ok) {
		throw new Error(await errorMessage(response, path, init?.method ?? 'GET'));
	}
	return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const getAssets = () => request<Position[]>('/assets');

export const getSummary = () => request<Summary>('/assets/summary');

export const getAsset = (symbol: string) =>
	request<Position>(`/assets/${encodeURIComponent(symbol)}`);

export const getChart = (symbol: string, window = 'tx') =>
	request<Chart>(`/assets/${encodeURIComponent(symbol)}/chart?window=${window}`);

export const setOpeningPosition = (
	symbol: string,
	body: { quantity: number; invested: number | null }
) =>
	request<Position>(`/assets/${encodeURIComponent(symbol)}/opening`, {
		method: 'PUT',
		body: JSON.stringify(body)
	});

export const getTransactions = (symbol: string) =>
	request<Transaction[]>(`/transactions?symbol=${encodeURIComponent(symbol)}`);

export const addTransaction = (transaction: NewTransaction) =>
	request<Transaction>('/transactions', {
		method: 'POST',
		body: JSON.stringify(transaction)
	});

export const deleteTransaction = (id: number) =>
	request<void>(`/transactions/${id}`, { method: 'DELETE' });




export async function getNote(): Promise<string> {
	// Plain text, so it does not go through request().
	const response = await fetch(`${BASE}/note`, { credentials: 'include' });
	if (response.status === 401) {
		session.expired();
		throw new Error('Session expired.');
	}
	if (!response.ok) throw new Error(`GET /note failed: ${response.status}`);
	return response.text();
}

/** The address a calendar subscribes to, token included. */
export const getFeedUrl = () => request<FeedUrl>('/note/feed-url');

export const getSession = () => request<Session>('/session');

export const login = (password: string) =>
	request<void>('/login', { method: 'POST', body: JSON.stringify({ password }) });

export const searchTickers = (query: string) =>
	request<SearchHit[]>(`/assets/search?q=${encodeURIComponent(query)}`);

export const createAsset = (asset: NewAsset) =>
	request<Position>('/assets', { method: 'POST', body: JSON.stringify(asset) });

export const updateAsset = (symbol: string, body: AssetUpdate) =>
	request<Position>(`/assets/${encodeURIComponent(symbol)}`, {
		method: 'PUT',
		body: JSON.stringify(body)
	});

export const deleteAsset = (symbol: string) =>
	request<void>(`/assets/${encodeURIComponent(symbol)}`, { method: 'DELETE' });

export const getEnvelopes = () => request<Envelope[]>('/envelopes');

export const setEnvelopeAmount = (name: string, monthlyAmount: number) =>
	request<Envelope>(`/envelopes/${encodeURIComponent(name)}`, {
		method: 'PUT',
		body: JSON.stringify({ name, monthly_amount: monthlyAmount })
	});

export const setEnvelopeStart = (name: string, body: EnvelopeStart) =>
	request<Envelope>(`/envelopes/${encodeURIComponent(name)}/start`, {
		method: 'PUT',
		body: JSON.stringify(body)
	});

export const clearEnvelopeStart = (name: string) =>
	request<Envelope>(`/envelopes/${encodeURIComponent(name)}/start`, { method: 'DELETE' });
