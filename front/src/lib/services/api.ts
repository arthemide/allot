/**
 * The one door the app knocks on, and the switch behind it.
 *
 * Components never pick a backend: they import from here, and here decides.
 * The app talks to the FastAPI server; /demo talks to an in-memory twin that
 * never leaves the tab. `demoBackend` is declared
 * `satisfies typeof http`, so an endpoint added there and forgotten in the
 * demo is a type error rather than a broken showroom.
 */
import * as http from './http';
import { demoBackend } from './demo';
import { demo } from '#lib/state/demo.svelte.js';

/** The half of the app that answers right now. */
const backend = () => (demo.enabled ? demoBackend : http);

export const getAssets: typeof http.getAssets = () => backend().getAssets();
export const getSummary: typeof http.getSummary = () => backend().getSummary();
export const getAsset: typeof http.getAsset = (symbol) => backend().getAsset(symbol);
export const getChart: typeof http.getChart = (symbol, window) =>
	backend().getChart(symbol, window);
export const setOpeningPosition: typeof http.setOpeningPosition = (symbol, body) =>
	backend().setOpeningPosition(symbol, body);
export const getTransactions: typeof http.getTransactions = (symbol) =>
	backend().getTransactions(symbol);
export const addTransaction: typeof http.addTransaction = (transaction) =>
	backend().addTransaction(transaction);
export const deleteTransaction: typeof http.deleteTransaction = (id) =>
	backend().deleteTransaction(id);
export const getNote: typeof http.getNote = () => backend().getNote();
export const getFeedUrl: typeof http.getFeedUrl = () => backend().getFeedUrl();
export const getSession: typeof http.getSession = () => backend().getSession();
export const login: typeof http.login = (password) => backend().login(password);
export const searchTickers: typeof http.searchTickers = (query) => backend().searchTickers(query);
export const createAsset: typeof http.createAsset = (asset) => backend().createAsset(asset);
export const importPreview: typeof http.importPreview = (snapshot) =>
	backend().importPreview(snapshot);
export const importSource: typeof http.importSource = (snapshot, placements, mappings) =>
	backend().importSource(snapshot, placements, mappings);
export const importCsv: typeof http.importCsv = (envelope, csv) =>
	backend().importCsv(envelope, csv);
export const connectorLogin: typeof http.connectorLogin = (login, password) =>
	backend().connectorLogin(login, password);
export const connectorAnswer: typeof http.connectorAnswer = (sessionId, answer) =>
	backend().connectorAnswer(sessionId, answer);
export const connectorAccounts: typeof http.connectorAccounts = (sessionId, envelopes) =>
	backend().connectorAccounts(sessionId, envelopes);
export const updateAsset: typeof http.updateAsset = (symbol, body) =>
	backend().updateAsset(symbol, body);
export const deleteAsset: typeof http.deleteAsset = (symbol) => backend().deleteAsset(symbol);
export const getEnvelopes: typeof http.getEnvelopes = () => backend().getEnvelopes();
export const setEnvelopeAmount: typeof http.setEnvelopeAmount = (name, monthlyAmount) =>
	backend().setEnvelopeAmount(name, monthlyAmount);
export const setEnvelopeStart: typeof http.setEnvelopeStart = (name, body) =>
	backend().setEnvelopeStart(name, body);
export const clearEnvelopeStart: typeof http.clearEnvelopeStart = (name) =>
	backend().clearEnvelopeStart(name);
