<script lang="ts">
	import { changeTicker, searchTickers } from '#lib/services/api.js';
	import type { Position, SearchHit } from '#lib/types/api.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Input } from '#lib/components/ui/input/index.js';

	// For a ticker picked wrong: the trades, the opening position and the
	// settings stay, only the listing the prices come from changes.
	let {
		position,
		onChanged
	}: {
		position: Position;
		onChanged: (symbol: string) => void;
	} = $props();

	let open = $state(false);
	let query = $state('');
	let hits = $state<SearchHit[] | null>(null);
	let error = $state('');
	let busy = $state(false);

	$effect(() => {
		if (open) return;
		query = error = '';
		hits = null;
	});

	async function search(event: SubmitEvent) {
		event.preventDefault();
		if (!query.trim()) return;
		error = '';
		busy = true;
		try {
			hits = await searchTickers(query.trim());
		} catch (e) {
			error = e instanceof Error ? e.message : 'The search failed.';
		} finally {
			busy = false;
		}
	}

	async function pick(hit: SearchHit) {
		const currency = hit.currency ? `, in ${hit.currency}` : '';
		if (!confirm(`Quote ${position.symbol} as ${hit.symbol}${currency} from now on?`)) return;
		error = '';
		busy = true;
		try {
			const moved = await changeTicker(position.symbol, hit.symbol);
			open = false;
			onChanged(moved.symbol);
		} catch (e) {
			error = e instanceof Error ? e.message : 'The ticker could not be changed.';
		} finally {
			busy = false;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="ghost" size="sm">Change ticker</Button>
		{/snippet}
	</Dialog.Trigger>

	<Dialog.Content class="sm:max-w-xl">
		<Dialog.Header>
			<Dialog.Title>Change the ticker of {position.symbol}</Dialog.Title>
			<Dialog.Description>
				The transactions, the opening position, the envelope and the weight stay as they are. The
				prices come from the new listing, and the currency becomes its own: check the recorded
				prices if it changes.
			</Dialog.Description>
		</Dialog.Header>

		<form class="flex gap-2" onsubmit={search}>
			<Input bind:value={query} placeholder="Name, ISIN or ticker" />
			<Button type="submit" variant="outline" disabled={busy}>Search</Button>
		</form>

		{#if hits && hits.length === 0}
			<p class="text-muted-foreground text-sm">No listing found.</p>
		{:else if hits}
			<ul class="divide-y rounded-md border text-sm">
				{#each hits as hit (hit.symbol)}
					<li>
						<button
							type="button"
							class="hover:bg-muted flex w-full items-baseline gap-3 px-3 py-2 text-left"
							disabled={busy || hit.symbol === position.symbol}
							onclick={() => pick(hit)}
						>
							<span class="font-mono">{hit.symbol}</span>
							<span class="text-muted-foreground min-w-0 flex-1 truncate">{hit.label}</span>
							<span class="text-muted-foreground text-xs">{hit.exchange} {hit.currency ?? ''}</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}

		{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
	</Dialog.Content>
</Dialog.Root>
