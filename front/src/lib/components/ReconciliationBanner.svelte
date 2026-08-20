<script lang="ts">
	import { setActualQuantity } from '$lib/services/api';
	import type { Position } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';

	let {
		position,
		onChange
	}: {
		position: Position;
		onChange: () => void;
	} = $props();

	let value = $state('');

	// Deliberately minimal: this replaces the automatic reconciliation, and the
	// figure is only ever compared, never fed into a calculation.
	async function save() {
		await setActualQuantity(position.symbol, value === '' ? null : Number(value));
		value = '';
		onChange();
	}

	const gap = $derived(position.quantity_gap);
	const drifted = $derived(gap !== null && Math.abs(gap) > 1e-8);
</script>

<div class="flex flex-wrap items-end gap-3 rounded-lg border p-4">
	<div>
		<label for="actual" class="text-muted-foreground text-xs uppercase">
			Quantity actually held on the platform
		</label>
		<Input
			id="actual"
			type="number"
			step="any"
			placeholder={position.actual_quantity?.toString() ?? 'not recorded'}
			bind:value
			class="w-48"
		/>
	</div>
	<Button variant="outline" onclick={save}>Save</Button>

	{#if position.actual_quantity !== null}
		<p class="text-sm {drifted ? 'text-amber-600' : 'text-green-600'}">
			{#if drifted}
				Gap of {gap?.toLocaleString('fr-FR', { maximumFractionDigits: 8 })} against the computed
				quantity.
			{:else}
				Matches the computed quantity.
			{/if}
		</p>
	{/if}
</div>
