<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import ExternalLink from "@lucide/svelte/icons/external-link";
	import Plus from "@lucide/svelte/icons/plus";

	interface SearchResult {
		symbol: string;
		name: string;
		exchange: string;
		type: string;
		price?: number;
	}

	type Props = {
		onAddStock?: (symbol: string) => void;
	};

	let { onAddStock }: Props = $props();

	let query = $state('');
	let results: SearchResult[] = $state([]);
	let loading = $state(false);
	let error = $state('');

	async function searchStocks() {
		if (!query.trim()) {
			results = [];
			return;
		}

		loading = true;
		error = '';

		try {
			const response = await fetch(
				`http://localhost:8000/stocks/search?q=${encodeURIComponent(query)}`
			);

			if (!response.ok) {
				throw new Error('Failed to fetch search results');
			}

			const data = await response.json();
			results = data.results || [];
			console.log("Fetched results:", results)
		} catch (e) {
			error = e instanceof Error ? e.message : 'An error occurred';
			results = [];
		} finally {
			loading = false;
		}
	}

	function handleInput() {
		// Debounce search
		clearTimeout(timeoutId);
		timeoutId = setTimeout(searchStocks, 300);
	}

	function openStockDetails(symbol: string) {
		// Open Yahoo Finance or Google Finance with stock symbol
		window.open(`https://finance.yahoo.com/quote/${symbol}`, '_blank');
	}

	function addStockToFund(stock: SearchResult) {
		if (onAddStock) {
			onAddStock(stock.symbol);
			// Clear search after adding
			query = '';
			results = [];
		}
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		const searchContainer = document.querySelector('.search-container');
		
		if (searchContainer && !searchContainer.contains(target)) {
			query = '';
			results = [];
		}
	}

	$effect(() => {
		document.addEventListener('click', handleClickOutside);
		
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});

	let timeoutId: ReturnType<typeof setTimeout>;
</script>

<div class="search-container">
	<div class="search-input-wrapper">
		<input
			type="text"
			bind:value={query}
			on:input={handleInput}
			placeholder="Search for stocks (e.g., AAPL, Tesla, Bitcoin)..."
			class="search-input"
		/>
		{#if loading}
			<div class="spinner"></div>
		{:else if results.length === 0 && query && !loading}
			<div class="no-results">No results found for "{query}"</div>
		{/if}
	</div>

	{#if error}
		<div class="error-message">
			{error}
		</div>
	{/if}

	{#if results.length > 0}
		<div class="results-list">
			{#each results as result}
				<div class="result-item">
					<div class="result-symbol">{result.symbol}</div>
					<div class="result-info">
						<div class="result-name">{result.name}</div>
						<div class="result-meta">
							{result.exchange}
							{#if result.type}
								• {result.type}
							{/if}
						</div>
					</div>
					<div class="result-price">
					<div class="result-actions">
						<Button
							size="icon-sm"
							variant="outline"
							onclick={() => openStockDetails(result.symbol)}
							title="View details"
						>
							<ExternalLink class="w-4 h-4" />
						</Button>
						<Button
							size="icon-sm"
							onclick={() => addStockToFund(result)}
							title="Add to fund"
						>
							<Plus class="w-4 h-4" />
						</Button>
					</div>
						{#if result.price !== undefined}
							{result.price.toFixed(2)}€
						{:else}
							N/A
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.search-container {
		width: 100%;
		max-width: 600px;
		margin: 0 auto;
		position: relative;
		z-index: 50;
	}

	.search-input-wrapper {
		position: relative;
		display: flex;
		align-items: center;
	}

	.search-input {
		width: 100%;
		padding: 12px 16px;
		font-size: 16px;
		border: 2px solid #e2e8f0;
		border-radius: 8px;
		outline: none;
		transition: border-color 0.2s;
	}

	.search-input:focus {
		border-color: #3b82f6;
	}

	.spinner {
		position: absolute;
		right: 16px;
		width: 20px;
		height: 20px;
		border: 2px solid #e2e8f0;
		border-top-color: #3b82f6;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.error-message {
		margin-top: 12px;
		padding: 12px;
		background-color: #fee2e2;
		color: #dc2626;
		border-radius: 6px;
		font-size: 14px;
	}

	.results-list {
		margin-top: 12px;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		overflow: hidden;
		background-color: white;
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
		position: absolute;
		width: 100%;
		z-index: 50;
	}

	.result-item {
		display: flex;
		align-items: center;
		padding: 12px 16px;
		border-bottom: 1px solid #e2e8f0;
		transition: background-color 0.2s;
		position: relative;
	}

	.result-item:last-child {
		border-bottom: none;
	}

	.result-item:hover {
		background-color: #f8fafc;
	}

	.result-symbol {
		font-weight: 600;
		font-size: 16px;
		color: #1e293b;
		min-width: 100px;
	}

	.result-info {
		flex: 1;
	}

	.result-name {
		font-size: 14px;
		color: #475569;
		margin-bottom: 2px;
	}

	.result-meta {
		font-size: 12px;
		color: #94a3b8;
	}

	.result-price {
		font-size: 12px;
		color: #94a3b8;
		min-width: 60px;
		text-align: right;
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.result-actions {
		display: flex;
		flex-direction: row;
		gap: 8px;
		opacity: 0;
		transition: opacity 0.2s;
	}

	.result-item:hover .result-actions {
		opacity: 1;
	}

	.no-results {
		margin-top: 12px;
		padding: 16px;
		text-align: center;
		color: #64748b;
		font-size: 14px;
	}
</style>
