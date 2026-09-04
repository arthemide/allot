<script lang="ts">
	import { createAsset, getAssets, getEnvelopes, searchTickers } from '$lib/services/api';
	import { refresh } from '$lib/state/refresh.svelte';
	import type { Envelope, SearchHit } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { formatMoney } from '$lib/utils';

	// Lives in the header, so it fetches what it needs instead of taking props.
	let envelopes = $state<Envelope[]>([]);
	let tracked = $state<string[]>([]);

	let open = $state(false);
	let query = $state('');
	let hits = $state<SearchHit[]>([]);
	let searching = $state(false);
	let searched = $state(false);
	let error = $state('');
	// Envelope the next added asset lands in; free text so a new one can be
	// created on the spot.
	let envelope = $state('');

	$effect(() => {
		if (!open) return;
		Promise.all([getEnvelopes(), getAssets()])
			.then(([e, assets]) => {
				envelopes = e;
				tracked = assets.map((a) => a.symbol);
			})
			.catch(() => {
				/* the dialog still works without the hints */
			});
	});

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
			refresh.bump();
			open = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not add the asset.';
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="outline" size="sm">Add an asset</Button>
		{/snippet}
	</Dialog.Trigger>

	<Dialog.Content class="sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Add an asset</Dialog.Title>
			<Dialog.Description>
				Exchange suffixes matter (WPEA.PA, VWCE.DE, ETH-USD). Search by name or symbol; a result
				with no price does not answer and should not be picked.
			</Dialog.Description>
		</Dialog.Header>

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
				<li
					class="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-3 py-2 text-sm"
				>
					<div class="flex min-w-0 flex-1 basis-48 items-baseline gap-2">
						<span class="shrink-0 font-mono font-medium">{hit.symbol}</span>
						<span class="text-muted-foreground truncate">{hit.label}</span>
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
	</Dialog.Content>
</Dialog.Root>
