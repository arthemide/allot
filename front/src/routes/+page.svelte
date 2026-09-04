<script lang="ts">
	import AssetChart from '$lib/components/AssetChart.svelte';
	import GlobalSummary from '$lib/components/GlobalSummary.svelte';
	import OpeningPosition from '$lib/components/OpeningPosition.svelte';
	import PositionBanner from '$lib/components/PositionBanner.svelte';
	import TransactionTable from '$lib/components/TransactionTable.svelte';
	import { browser } from '$app/environment';
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { getAssets, getChart, getEnvelopes } from '$lib/services/api';
	import { refresh as refreshSignal } from '$lib/state/refresh.svelte';
	import type { Chart, Envelope, Position } from '$lib/types/api';

	// Sentinel value of the selector: totals and settings instead of one asset.
	const ALL = '*';

	// The address is the selection: the note links to ?asset=SYMBOL, and going
	// back or clicking the title lands here rather than in a second state.
	const inUrl = $derived(page.url.searchParams.get('asset') ?? ALL);

	let positions = $state<Position[]>([]);
	let envelopes = $state<Envelope[]>([]);
	let selected = $state<string>(ALL);
	let chart = $state<Chart | null>(null);
	let window_ = $state('tx');
	let loading = $state(true);
	let error = $state('');

	const showingAll = $derived(selected === ALL);
	const position = $derived(positions.find((p) => p.symbol === selected) ?? null);

	async function loadPositions() {
		try {
			[positions, envelopes] = await Promise.all([getAssets(), getEnvelopes()]);
			// Deleted since, or a link naming something untracked.
			if (!showingAll && !positions.some((p) => p.symbol === selected)) select(ALL);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not reach the API.';
		} finally {
			loading = false;
		}
	}

	async function loadChart() {
		if (showingAll || !selected) {
			chart = null;
			return;
		}
		chart = await getChart(selected, window_);
	}

	async function refresh() {
		await loadPositions();
		await loadChart();
	}

	$effect(() => {
		// Re-reads when the header's search adds an asset.
		refreshSignal.tick;
		loadPositions();
	});

	$effect(() => {
		selected;
		window_;
		loadChart();
	});

	$effect(() => {
		selected = inUrl;
	});

	function select(symbol: string) {
		selected = symbol;
		if (!browser) return;
		const url = new URL(page.url);
		if (symbol === ALL) url.searchParams.delete('asset');
		else url.searchParams.set('asset', symbol);
		replaceState(url, page.state);
	}
</script>

<svelte:head><title>Allot</title></svelte:head>

<div class="mx-auto max-w-6xl space-y-6 p-6">
	{#if loading}
		<p class="text-muted-foreground">Loading...</p>
	{:else if error}
		<p class="text-red-600">{error}</p>
	{:else}
		<div class="flex flex-wrap items-center gap-3">
			<label for="asset" class="text-sm font-medium">Asset</label>
			<select
				id="asset"
				value={selected}
				onchange={(e) => select(e.currentTarget.value)}
				class="border-input bg-background h-9 min-w-64 rounded-md border px-3 text-sm"
			>
				<option value={ALL}>* All assets (totals and settings)</option>
				{#each positions as p (p.symbol)}
					<option value={p.symbol}>{p.envelope} - {p.symbol} ({p.label})</option>
				{/each}
			</select>
		</div>

		{#if showingAll}
			<GlobalSummary {positions} onChange={refresh} onSelect={select} />
		{:else if position}
			<PositionBanner {position} />

			{#if chart}
				<div class="space-y-3 rounded-lg border p-4">
					<div class="flex flex-wrap items-center gap-2">
						{#each [['tx', 'Since first buy'], ['1y', '1 year'], ['3y', '3 years'], ['5y', '5 years'], ['max', 'Max']] as [value, label] (value)}
							<button
								type="button"
								class="rounded-md border px-2 py-1 text-xs {window_ === value
									? 'bg-primary text-primary-foreground'
									: 'hover:bg-muted'}"
								onclick={() => (window_ = value)}
							>
								{label}
							</button>
						{/each}
					</div>
					<AssetChart
						transactions={chart.transactions}
						priceHistory={chart.prices}
						prumHistory={chart.prum}
						currency={chart.currency}
					/>
				</div>
			{/if}

			<TransactionTable {position} transactions={chart?.transactions ?? []} onChange={refresh}>
				{#snippet actions()}
					<OpeningPosition {position} onChange={refresh} />
				{/snippet}
			</TransactionTable>
		{/if}
	{/if}
</div>
