<script lang="ts">
	import { addTransaction, deleteTransaction } from '$lib/services/api';
	import type { Position, Transaction } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import { formatMoney } from '$lib/utils';

	let {
		position,
		transactions,
		onChange,
		actions
	}: {
		position: Position;
		transactions: Transaction[];
		onChange: () => void;
		// Extra buttons for the toolbar, so rarely used forms stay out of the way.
		actions?: import('svelte').Snippet;
	} = $props();

	let open = $state(false);

	let date = $state(new Date().toISOString().slice(0, 10));
	let side = $state<'buy' | 'sell'>('buy');
	let quantity = $state('');
	let unitPrice = $state('');
	let fees = $state('0');
	let error = $state('');
	let saving = $state(false);

	const money = $derived((value: number) => formatMoney(value, position.currency, 4));

	// Prefill the price with the current quote, still editable.
	$effect(() => {
		if (position.price !== null) unitPrice = String(position.price);
	});

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		const parsed = {
			quantity: Number(quantity),
			unit_price: Number(unitPrice),
			fees: Number(fees || '0')
		};
		if (!(parsed.quantity > 0) || !(parsed.unit_price > 0)) {
			error = 'Quantity and price must be greater than zero.';
			return;
		}
		saving = true;
		try {
			await addTransaction({ symbol: position.symbol, date, side, ...parsed });
			quantity = '';
			fees = '0';
			onChange();
			open = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save the transaction.';
		} finally {
			saving = false;
		}
	}

	async function remove(tx: Transaction) {
		// The position is recomputed from these rows: a silent delete would
		// move the PRUM with no way back.
		if (!confirm(`Delete the ${tx.side} of ${tx.quantity} on ${tx.date}?`)) return;
		await deleteTransaction(tx.id);
		onChange();
	}
</script>

<div class="flex items-center justify-between gap-2">
	<h2 class="font-semibold">Transactions</h2>
	<div class="flex items-center gap-1">
		{@render actions?.()}

		<Dialog.Root bind:open>
			<Dialog.Trigger>
				{#snippet child({ props })}
					<Button {...props} size="sm" title="Add a transaction">+</Button>
				{/snippet}
			</Dialog.Trigger>

			<Dialog.Content class="max-w-xl">
				<Dialog.Header>
					<Dialog.Title>Add a transaction</Dialog.Title>
					<Dialog.Description>
						One order: the price you paid per unit on that day.
					</Dialog.Description>
				</Dialog.Header>

				<form class="space-y-3" onsubmit={submit}>
					<div class="flex flex-wrap items-end gap-3">
						<div class="space-y-1">
							<label for="tx-date" class="text-muted-foreground block text-xs uppercase">Date</label>
							<Input id="tx-date" type="date" bind:value={date} required class="w-40" />
						</div>
						<div class="space-y-1">
							<label for="tx-side" class="text-muted-foreground block text-xs uppercase">Side</label>
							<select
								id="tx-side"
								bind:value={side}
								class="border-input bg-background h-9 rounded-md border px-2 text-sm"
							>
								<option value="buy">buy</option>
								<option value="sell">sell</option>
							</select>
						</div>
						<div class="space-y-1">
							<label for="tx-quantity" class="text-muted-foreground block text-xs uppercase">
								Quantity
							</label>
							<Input id="tx-quantity" type="number" step="any" bind:value={quantity} class="w-36" />
						</div>
						<div class="space-y-1">
							<label for="tx-price" class="text-muted-foreground block text-xs uppercase">
								Price paid / unit
							</label>
							<Input id="tx-price" type="number" step="any" bind:value={unitPrice} class="w-36" />
						</div>
						<div class="space-y-1">
							<label for="tx-fees" class="text-muted-foreground block text-xs uppercase">Fees</label>
							<Input id="tx-fees" type="number" step="any" bind:value={fees} class="w-28" />
						</div>
					</div>

					{#if error}
						<p class="text-sm text-red-600">{error}</p>
					{/if}

					<Dialog.Footer>
						<Button type="submit" disabled={saving}>{saving ? 'Saving...' : 'Add'}</Button>
					</Dialog.Footer>
				</form>
			</Dialog.Content>
		</Dialog.Root>
	</div>
</div>

<div class="rounded-lg border">
	<Table.Root>
		<Table.Header>
			<Table.Row>
				<Table.Head class="w-32 text-left">Date</Table.Head>
				<Table.Head class="w-20 text-left">Side</Table.Head>
				<Table.Head class="text-right">Quantity</Table.Head>
				<Table.Head class="text-right">Price paid / unit</Table.Head>
				<Table.Head class="text-right">Fees</Table.Head>
				<Table.Head class="text-right">Total</Table.Head>
				<Table.Head class="w-16"></Table.Head>
			</Table.Row>
		</Table.Header>
		<Table.Body>
			{#each transactions as tx (tx.id)}
				<Table.Row>
					<Table.Cell class="w-32 text-left tabular-nums">{tx.date}</Table.Cell>
					<Table.Cell class="w-20 text-left">
						<span class={tx.side === 'sell' ? 'text-red-600' : 'text-green-600'}>{tx.side}</span>
					</Table.Cell>
					<Table.Cell class="text-right tabular-nums">{tx.quantity}</Table.Cell>
					<Table.Cell class="text-right tabular-nums">{money(tx.unit_price)}</Table.Cell>
					<Table.Cell class="text-right tabular-nums">{money(tx.fees)}</Table.Cell>
					<Table.Cell class="text-right tabular-nums">
						{money(tx.quantity * tx.unit_price + tx.fees)}
					</Table.Cell>
					<Table.Cell class="w-16 text-right">
						<button
							type="button"
							title="Delete this transaction"
							aria-label="Delete the transaction of {tx.date}"
							class="text-muted-foreground/40 hover:text-destructive px-2 leading-none
								transition-colors"
							onclick={() => remove(tx)}
						>
							&times;
						</button>
					</Table.Cell>
				</Table.Row>
			{:else}
				<Table.Row>
					<Table.Cell colspan={7} class="text-muted-foreground py-6 text-center">
						No transaction yet.
					</Table.Cell>
				</Table.Row>
			{/each}
		</Table.Body>
	</Table.Root>
</div>
