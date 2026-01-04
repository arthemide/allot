interface SearchResult {
	symbol: string;
	name: string;
	exchange: string;
	type: string;
	price?: number;
}

interface StockSearchState {
	query: string;
	results: SearchResult[];
	loading: boolean;
	error: string;
	showResults: boolean;
}

export function useStockSearch() {
	let state = $state<StockSearchState>({
		query: '',
		results: [],
		loading: false,
		error: '',
		showResults: false
	});

	let timeoutId: ReturnType<typeof setTimeout>;

	async function search(query: string) {
		if (!query.trim() || query.length < 1) {
			state.results = [];
			state.showResults = false;
			return;
		}

		state.loading = true;
		state.error = '';

		try {
			const response = await fetch(
				`http://localhost:8000/stocks/search?q=${encodeURIComponent(query)}`
			);

			if (!response.ok) {
				throw new Error('Failed to fetch search results');
			}

			const data = await response.json();
			state.results = data.results || [];
			state.showResults = state.results.length > 0;
		} catch (e) {
			state.error = e instanceof Error ? e.message : 'An error occurred';
			state.results = [];
			state.showResults = false;
		} finally {
			state.loading = false;
		}
	}

	function debouncedSearch(query: string, delay = 300) {
		clearTimeout(timeoutId);
		timeoutId = setTimeout(() => search(query), delay);
	}

	function clearResults() {
		state.results = [];
		state.showResults = false;
		state.error = '';
	}

	function setShowResults(show: boolean) {
		state.showResults = show;
	}

	return {
		get state() {
			return state;
		},
		search,
		debouncedSearch,
		clearResults,
		setShowResults
	};
}

export type { SearchResult };
