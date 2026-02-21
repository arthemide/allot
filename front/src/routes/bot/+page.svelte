<script lang="ts">
	import { onMount } from 'svelte';
	import { configApi, transactionApi, stockApi } from '$lib/services/api-calls';
	import type { AssetTransaction, FundConfig } from '$lib/types/config';
	import TransactionTimeline from '$lib/components/TransactionTimeline.svelte';
	import CumulativeInvestment from '$lib/components/CumulativeInvestment.svelte';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Table from '$lib/components/ui/table/index.js';

	let funds: FundConfig[] = $state([]);
	let selectedFundId: string = $state('');
	let transactions: AssetTransaction[] = $state([]);
	let selectedSymbol: string = $state('');
	let priceHistory: { date: string; price: number }[] = $state([]);
	let loading = $state(false);
	let error: string | null = $state(null);

	// Derived: unique symbols from all transactions
	let symbols = $derived([...new Set(transactions.map((tx) => tx.asset_symbol))].sort());

	// Derived: transactions filtered by selected symbol (for chart 2)
	let filteredTransactions = $derived(
		selectedSymbol ? transactions.filter((tx) => tx.asset_symbol === selectedSymbol) : transactions
	);

	async function loadFunds() {
		try {
			funds = await configApi.getAllConfigs();
		} catch (e) {
			error = 'Failed to load funds.';
		}
	}

	async function loadTransactions() {
		loading = true;
		error = null;
		try {
			transactions = await transactionApi.getAll(
				selectedFundId ? { fund_id: selectedFundId } : {}
			);
			// Auto-select first symbol
			const syms = [...new Set(transactions.map((tx) => tx.asset_symbol))].sort();
			selectedSymbol = syms[0] ?? '';
			await loadPriceHistory();
		} catch (e) {
			error = 'Failed to load transactions.';
			transactions = [];
		} finally {
			loading = false;
		}
	}

	async function loadPriceHistory() {
		const symbol = selectedSymbol;
		if (!symbol || transactions.length === 0) {
			priceHistory = [];
			return;
		}
		const txForSymbol = transactions.filter((tx) => tx.asset_symbol === symbol);
		if (txForSymbol.length === 0) { priceHistory = []; return; }
		const sorted = [...txForSymbol].sort(
			(a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
		);
		const start = new Date(sorted[0].timestamp).toISOString().slice(0, 10);
		const end = new Date().toISOString().slice(0, 10);
		try {
			priceHistory = await stockApi.getPriceHistory(symbol, start, end);
		} catch {
			priceHistory = [];
		}
	}

	async function onSymbolChange() {
		await loadPriceHistory();
	}

	onMount(async () => {
		await loadFunds();
		await loadTransactions();
	});

	function onFundChange() {
		loadTransactions();
	}

	function typeBadgeClass(type: string) {
		if (type === 'sell') return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
		return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
	}
</script>

<div class="container mx-auto max-w-5xl px-4 py-8">
	<h1 class="mb-6 text-2xl font-bold">DCA Bot — Transactions</h1>

	<!-- Fund selector -->
	<div class="mb-6">
		<label for="fund-select" class="mb-1 block text-sm font-medium">Fund</label>
		<select
			id="fund-select"
			bind:value={selectedFundId}
			onchange={onFundChange}
			class="rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
		>
			<option value="">All funds</option>
			{#each funds as fund}
				<option value={fund.id}>{fund.fund_name}</option>
			{/each}
		</select>
	</div>

	<!-- Error state -->
	{#if error}
		<p class="mb-4 rounded-md bg-red-100 px-4 py-3 text-sm text-red-700 dark:bg-red-900 dark:text-red-200">
			{error}
		</p>
	{/if}

	<!-- Loading state -->
	{#if loading}
		<div class="flex items-center justify-center py-16 text-muted-foreground">
			<span>Loading…</span>
		</div>

	<!-- Empty state -->
	{:else if transactions.length === 0}
		<div class="flex items-center justify-center py-16 text-muted-foreground">
			<span>No transactions for this fund.</span>
		</div>

	{:else}
		<!-- Charts -->
		<div class="mb-6 grid gap-6 md:grid-cols-1">
			<!-- Chart 1: cumulative investment (all assets) -->
			<Card.Root>
				<Card.Header>
					<Card.Title>Cumulative Investment</Card.Title>
				</Card.Header>
				<Card.Content>
					<CumulativeInvestment {transactions} />
				</Card.Content>
			</Card.Root>

			<!-- Chart 2: price per transaction + PRUM, filtered by pair -->
			<Card.Root>
				<Card.Header class="flex flex-row items-center justify-between gap-4">
					<Card.Title>Purchase Price per Transaction &amp; AVCO</Card.Title>
					{#if symbols.length > 1}
						<select
							bind:value={selectedSymbol}
							onchange={onSymbolChange}
							class="rounded-md border border-input bg-background px-2 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
						>
							{#each symbols as sym}
								<option value={sym}>{sym}</option>
							{/each}
						</select>
					{:else}
						<span class="text-sm text-muted-foreground">{selectedSymbol}</span>
					{/if}
				</Card.Header>
				<Card.Content>
					<TransactionTimeline transactions={filteredTransactions} {priceHistory} />
				</Card.Content>
			</Card.Root>
		</div>

		<!-- Transactions table -->
		<Card.Root>
			<Card.Header>
				<Card.Title>Transaction History</Card.Title>
			</Card.Header>
			<Card.Content>
				<Table.Root>
					<Table.Header>
						<Table.Row>
							<Table.Head>Date</Table.Head>
							<Table.Head>Asset</Table.Head>
							<Table.Head>Type</Table.Head>
							<Table.Head class="text-right">Quantity</Table.Head>
							<Table.Head class="text-right">Price</Table.Head>
							<Table.Head class="text-right">Total</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each transactions as tx}
							<Table.Row>
								<Table.Cell class="text-sm">
									{new Date(tx.timestamp).toLocaleDateString('en-GB', {
										year: 'numeric',
										month: 'short',
										day: 'numeric'
									})}
								</Table.Cell>
								<Table.Cell>
									<span class="font-medium">{tx.asset_symbol}</span>
									{#if tx.asset_name}
										<span class="ml-1 text-xs text-muted-foreground">{tx.asset_name}</span>
									{/if}
								</Table.Cell>
								<Table.Cell>
									<span class="rounded-full px-2 py-0.5 text-xs font-medium {typeBadgeClass(tx.transaction_type)}">
										{tx.transaction_type}
									</span>
								</Table.Cell>
								<Table.Cell class="text-right text-sm">{tx.quantity.toFixed(6)}</Table.Cell>
								<Table.Cell class="text-right text-sm">${tx.price.toFixed(4)}</Table.Cell>
								<Table.Cell class="text-right font-medium">${tx.total_cost.toFixed(2)}</Table.Cell>
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			</Card.Content>
		</Card.Root>
	{/if}
</div>
