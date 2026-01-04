<script lang="ts">
	import type { SearchResult } from '$lib/hooks/useStockSearch.svelte';

	type Props = {
		results: SearchResult[];
		show: boolean;
		onSelect: (result: SearchResult) => void;
	};

	let { results, show, onSelect }: Props = $props();
</script>

{#if show && results.length > 0}
	<div class="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-60 overflow-auto">
		{#each results as result}
			<button
				type="button"
				class="w-full px-3 py-2 text-left hover:bg-slate-50 flex items-center justify-between border-b border-slate-100 last:border-b-0"
				onclick={() => onSelect(result)}
			>
				<div class="flex-1">
					<div class="font-semibold text-sm">{result.symbol}</div>
					<div class="text-xs text-slate-600">{result.name}</div>
					<div class="text-xs text-slate-400">{result.exchange} • {result.type}</div>
				</div>
				{#if result.price !== undefined}
					<div class="text-sm font-medium ml-2">{result.price.toFixed(2)}€</div>
				{/if}
			</button>
		{/each}
	</div>
{/if}
