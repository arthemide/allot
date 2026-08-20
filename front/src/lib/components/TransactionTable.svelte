<script lang="ts">
	import { addTransaction, deleteTransaction } from '$lib/services/api';
	import type { Position, Transaction } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import { formatMoney } from '$lib/utils';

	let {
		position,
		transactions,
		onChange
	}: {
		position: Position;
		transactions: Transaction[];
		onChange: () => void;
	} = $props();



	// The add form lives in the first row of the table, not in a dialog.
	let date = $state(new Date().toISOString().slice(0, 10));
	let side = $state<'buy' | 'sell'>('buy');
	let quantity = $state('');
	let unitPrice = $state('');
	let fees = $state('0');
	let error = $state('');
	let saving = $state(false);

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
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save the transaction.';
		} finally {
			saving = false;
		}
	}

	async function remove(id: number) {
		await deleteTransaction(id);
		onChange();
	}

	const money = $derived((value: number) => formatMoney(value, position.currency, 4));
</script>

<div class="rounded-lg border">
	<Table.Root>
		<Table.Header>
			<Table.Row>
				<Table.Head>Date</Table.Head>
				<Table.Head>Side</Table.Head>
				<Table.Head class="text-right">Quantity</Table.Head>
				<Table.Head class="text-right">Unit price</Table.Head>
				<Table.Head class="text-right">Fees</Table.Head>
				<Table.Head class="text-right">Total</Table.Head>
				<Table.Head></Table.Head>
			</Table.Row>
		</Table.Header>
		<Table.Body>
			<Table.Row class="bg-muted/40">
				<Table.Cell><Input type="date" bind:value={date} form="add-tx" required /></Table.Cell>
				<Table.Cell>
					<select
						bind:value={side}
						form="add-tx"
						class="border-input bg-background h-9 rounded-md border px-2 text-sm"
					>
						<option value="buy">buy</option>
						<option value="sell">sell</option>
					</select>
				</Table.Cell>
				<Table.Cell>
					<Input type="number" step="any" placeholder="0" bind:value={quantity} form="add-tx" />
				</Table.Cell>
				<Table.Cell>
					<Input type="number" step="any" bind:value={unitPrice} form="add-tx" />
				</Table.Cell>
				<Table.Cell><Input type="number" step="any" bind:value={fees} form="add-tx" /></Table.Cell>
				<Table.Cell></Table.Cell>
				<Table.Cell>
					<form id="add-tx" onsubmit={submit}>
						<Button type="submit" size="sm" disabled={saving}>
							{saving ? 'Saving…' : 'Add'}
						</Button>
					</form>
				</Table.Cell>
			</Table.Row>

			{#each transactions as tx (tx.id)}
				<Table.Row>
					<Table.Cell>{tx.date}</Table.Cell>
					<Table.Cell>
						<span class={tx.side === 'sell' ? 'text-red-600' : 'text-green-600'}>{tx.side}</span>
					</Table.Cell>
					<Table.Cell class="text-right">{tx.quantity}</Table.Cell>
					<Table.Cell class="text-right">{money(tx.unit_price)}</Table.Cell>
					<Table.Cell class="text-right">{money(tx.fees)}</Table.Cell>
					<Table.Cell class="text-right">
						{money(tx.quantity * tx.unit_price + tx.fees)}
					</Table.Cell>
					<Table.Cell class="text-right">
						<Button variant="ghost" size="sm" onclick={() => remove(tx.id)}>Delete</Button>
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

{#if error}
	<p class="mt-2 text-sm text-red-600">{error}</p>
{/if}
