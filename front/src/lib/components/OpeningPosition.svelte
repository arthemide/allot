<script lang="ts">
	import { setOpeningPosition } from '$lib/services/api';
	import type { Position } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { formatMoney } from '$lib/utils';

	let {
		position,
		onChange
	}: {
		position: Position;
		onChange: () => void;
	} = $props();

	let open = $state(false);
	let quantity = $state('');
	let invested = $state('');
	let error = $state('');
	let saving = $state(false);

	$effect(() => {
		position.symbol;
		quantity = position.base_quantity ? String(position.base_quantity) : '';
		invested =
			position.base_quantity && position.base_prum
				? String(round(position.base_quantity * position.base_prum))
				: '';
	});

	function round(value: number): number {
		return Math.round(value * 100) / 100;
	}

	// Shown live, so what will be stored is visible before saving.
	const derivedPrum = $derived(
		Number(quantity) > 0 && Number(invested) > 0 ? Number(invested) / Number(quantity) : null
	);

	async function save() {
		error = '';
		saving = true;
		try {
			await setOpeningPosition(position.symbol, {
				quantity: Number(quantity || '0'),
				invested: invested === '' ? null : Number(invested)
			});
			onChange();
			open = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save.';
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="ghost" size="sm">
				Opening position{position.base_quantity ? ' *' : ''}
			</Button>
		{/snippet}
	</Dialog.Trigger>

	<Dialog.Content class="max-w-xl">
		<Dialog.Header>
			<Dialog.Title>Opening position</Dialog.Title>
			<Dialog.Description>
				For a holding built before you started tracking, when the individual buys are gone. Take
				the units held and the total paid off a statement; the PRUM follows. Leave the quantity at
				0 if every buy is recorded as a transaction.
			</Dialog.Description>
		</Dialog.Header>

		<div class="flex flex-wrap items-end gap-3">
			<div class="space-y-1">
				<label for="open-qty" class="text-muted-foreground block text-xs uppercase">Units held</label>
				<Input id="open-qty" type="number" step="any" bind:value={quantity} class="w-40" />
			</div>
			<div class="space-y-1">
				<label for="open-amount" class="text-muted-foreground block text-xs uppercase">
					Total paid
				</label>
				<Input id="open-amount" type="number" step="any" bind:value={invested} class="w-40" />
			</div>
			<div class="space-y-1">
				<span class="text-muted-foreground block text-xs uppercase">Resulting PRUM</span>
				<div class="flex h-9 items-center text-sm font-medium tabular-nums">
					{derivedPrum === null ? '-' : formatMoney(derivedPrum, position.currency, 4)}
				</div>
			</div>
			<Button variant="outline" onclick={save} disabled={saving}>
				{saving ? 'Saving...' : 'Save'}
			</Button>
		</div>

		{#if error}
			<p class="text-sm text-red-600">{error}</p>
		{/if}
	</Dialog.Content>
</Dialog.Root>
