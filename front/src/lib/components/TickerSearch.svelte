<script lang="ts">
	import { createAsset, searchTickers } from '$lib/services/api';
	import type { Envelope, SearchHit } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { formatMoney } from '$lib/utils';

	let {
		envelopes,
		tracked = [],
		onAdded
	}: {
		envelopes: Envelope[];
		tracked?: string[];
		onAdded: () => void;
	} = $props();

	let query = $state('');
	let hits = $state<SearchHit[]>([]);
	let searching = $state(false);
	let searched = $state(false);
	let error = $state('');
	// Envelope the next added asset lands in; free text so a new one can be
	// created on the spot.
	let envelope = $state('');

	async function run(event: SubmitEvent) {
		event.preventDefault();
		if (!query.trim()) return;
		error = '';
		searching = true;
		try {
			hits = await searchTickers(query.trim());
			searched = true;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Search failed.';
		} finally {
			searching = false;
		}
	}

	async function add(hit: SearchHit) {
		if (!envelope.trim()) {
			error = 'Pick an envelope first.';
			return;
		}
		error = '';
		try {
			await createAsset({
				symbol: hit.symbol,
				label: hit.label,
				envelope: envelope.trim().toUpperCase(),
				currency: hit.currency ?? 'EUR',
				weight: 1
			});
			hits = hits.filter((h) => h.symbol !== hit.symbol);
			onAdded();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not add the asset.';
		}
	}
</script>

<div class="space-y-3 rounded-lg border p-4">
	<h2 class="font-semibold">Find a ticker</h2>
	<p class="text-muted-foreground text-sm">
		Exchange suffixes matter (WPEA.PA, VWCE.DE, ETH-USD). Search by name or symbol; a result with
		no price does not answer and should not be picked.
	</p>

	<form class="flex flex-wrap items-end gap-3" onsubmit={run}>
		<div class="space-y-1">
			<label for="q" class="text-muted-foreground block text-xs uppercase">Name or symbol</label>
			<Input id="q" bind:value={query} placeholder="msci world" class="w-64" />
		</div>
		<div class="space-y-1">
			<label for="env" class="text-muted-foreground block text-xs uppercase">Add to envelope</label>
			<input
				id="env"
				bind:value={envelope}
				list="envelope-list"
				placeholder="PEA"
				class="border-input bg-background h-9 w-40 rounded-md border px-3 text-sm"
			/>
			<datalist id="envelope-list">
				{#each envelopes as e (e.name)}
					<option value={e.name}></option>
				{/each}
			</datalist>
		</div>
		<Button type="submit" disabled={searching}>{searching ? 'Searching...' : 'Search'}</Button>
	</form>

	{#if error}
		<p class="text-sm text-red-600">{error}</p>
	{/if}

	{#if hits.length > 0}
		<ul class="divide-y rounded-md border">
			{#each hits as hit (hit.symbol)}
				<li class="flex items-center justify-between gap-3 px-3 py-2 text-sm">
					<div class="min-w-0">
						<span class="font-mono font-medium">{hit.symbol}</span>
						<span class="text-muted-foreground ml-2 truncate">{hit.label}</span>
					</div>
					<div class="flex shrink-0 items-center gap-3">
						{#if hit.price === null}
							<span class="text-amber-600">no quote</span>
						{:else}
							<span class="tabular-nums">{formatMoney(hit.price, hit.currency)}</span>
						{/if}
						{#if tracked.includes(hit.symbol)}
							<span class="text-muted-foreground text-xs">already tracked</span>
						{/if}
						<Button
							size="sm"
							variant="outline"
							onclick={() => add(hit)}
							disabled={hit.price === null || tracked.includes(hit.symbol)}
						>
							Add
						</Button>
					</div>
				</li>
			{/each}
		</ul>
	{:else if searched && !searching}
		<p class="text-muted-foreground text-sm">
			Nothing found. Yahoo's search is literal: try the bare symbol, like WPEA or VWCE.
		</p>
	{/if}
</div>
