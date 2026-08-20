<script lang="ts">
	import AssetChart from '$lib/components/AssetChart.svelte';
	import MonthlyNote from '$lib/components/MonthlyNote.svelte';
	import PositionBanner from '$lib/components/PositionBanner.svelte';
	import TransactionTable from '$lib/components/TransactionTable.svelte';
	import { getAssets, getChart, setManualValue } from '$lib/services/api';
	import type { Chart, Position } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';

	let positions = $state<Position[]>([]);
	let selected = $state<string>('');
	let chart = $state<Chart | null>(null);
	let loading = $state(true);
	let error = $state('');
	let manualValue = $state('');

	const position = $derived(positions.find((p) => p.symbol === selected) ?? null);
	const isManual = $derived(position?.price_source === 'manual');

	async function loadPositions() {
		try {
			positions = await getAssets();
			if (!selected && positions.length > 0) selected = positions[0].symbol;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not reach the API.';
		} finally {
			loading = false;
		}
	}

	async function loadChart() {
		if (!selected || isManual) {
			chart = null;
			return;
		}
		chart = await getChart(selected);
	}

	async function refresh() {
		await loadPositions();
		await loadChart();
	}

	async function saveManualValue() {
		if (!position) return;
		await setManualValue(position.symbol, Number(manualValue));
		manualValue = '';
		await loadPositions();
	}

	$effect(() => {
		loadPositions();
	});

	$effect(() => {
		selected;
		loadChart();
	});
</script>

<svelte:head><title>Wealth tracking</title></svelte:head>

<div class="mx-auto max-w-6xl space-y-6 p-6">
	{#if loading}
		<p class="text-muted-foreground">Loading…</p>
	{:else if error}
		<p class="text-red-600">{error}</p>
	{:else}
		<div class="flex flex-wrap items-center gap-3">
			<label for="asset" class="text-sm font-medium">Asset</label>
			<select
				id="asset"
				bind:value={selected}
				class="border-input bg-background h-9 min-w-56 rounded-md border px-3 text-sm"
			>
				{#each positions as p (p.symbol)}
					<option value={p.symbol}>{p.envelope} - {p.symbol} ({p.label})</option>
				{/each}
			</select>
		</div>

		{#if position}
			<PositionBanner {position} />

			{#if isManual}
				<div class="space-y-3 rounded-lg border p-4">
					<p class="text-muted-foreground text-sm">
						{position.symbol} has no ticker: no PRUM, no chart, no simulator. Enter its value by hand.
					</p>
					<div class="flex gap-2">
						<Input
							type="number"
							step="any"
							placeholder="Current value"
							bind:value={manualValue}
							class="max-w-48"
						/>
						<Button onclick={saveManualValue}>Save</Button>
					</div>
				</div>
			{:else}
				{#if chart}
					<div class="rounded-lg border p-4">
						<AssetChart
							transactions={chart.transactions}
							priceHistory={chart.prices}
							prumHistory={chart.prum}
							currency={chart.currency}
						/>
					</div>
				{/if}

				<TransactionTable {position} transactions={chart?.transactions ?? []} onChange={refresh} />
			{/if}
		{/if}

		<MonthlyNote />
	{/if}
</div>
