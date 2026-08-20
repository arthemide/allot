<script lang="ts">
	import { simulate } from '$lib/services/api';
	import type { Position, Simulation } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { formatMoney } from '$lib/utils';

	let { position }: { position: Position } = $props();

	let amount = $state('');
	let fees = $state('0');
	let targetPrum = $state('');
	let result = $state<Simulation | null>(null);
	let error = $state('');
	let running = $state(false);

	const money = $derived((value: number | null) => formatMoney(value, position.currency));

	// A new asset resets the panel: figures from another asset would mislead.
	$effect(() => {
		position.symbol;
		result = null;
		error = '';
	});

	async function run() {
		error = '';
		const body: { amount?: number; fees?: number; target_prum?: number } = {};
		if (amount) {
			body.amount = Number(amount);
			body.fees = Number(fees || '0');
		}
		if (targetPrum) body.target_prum = Number(targetPrum);
		if (body.amount === undefined && body.target_prum === undefined) {
			error = 'Enter an amount, a target PRUM, or both.';
			return;
		}
		running = true;
		try {
			result = await simulate(position.symbol, body);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Simulation failed.';
		} finally {
			running = false;
		}
	}
</script>

<div class="space-y-4 rounded-lg border p-4">
	<h2 class="font-semibold">Simulator</h2>

	<div class="flex flex-wrap items-end gap-3">
		<div>
			<label for="sim-amount" class="text-muted-foreground text-xs uppercase">Amount to invest</label>
			<Input id="sim-amount" type="number" step="any" bind:value={amount} class="w-36" />
		</div>
		<div>
			<label for="sim-fees" class="text-muted-foreground text-xs uppercase">Fees</label>
			<Input id="sim-fees" type="number" step="any" bind:value={fees} class="w-24" />
		</div>
		<div>
			<label for="sim-target" class="text-muted-foreground text-xs uppercase">Target PRUM</label>
			<Input id="sim-target" type="number" step="any" bind:value={targetPrum} class="w-36" />
		</div>
		<Button onclick={run} disabled={running}>{running ? 'Computing…' : 'Simulate'}</Button>
	</div>

	{#if error}
		<p class="text-sm text-red-600">{error}</p>
	{/if}

	{#if result}
		<div class="space-y-2 text-sm">
			<p class="text-muted-foreground">
				Now: {result.quantity.toLocaleString('fr-FR', { maximumFractionDigits: 8 })} at a PRUM of
				{money(result.prum)}, price {money(result.price)}.
			</p>

			{#if result.buy}
				<p>
					Investing <strong>{money(result.buy.amount)}</strong>
					{#if result.buy.fees > 0}(fees {money(result.buy.fees)} included){/if}
					buys
					<strong>{result.buy.quantity.toLocaleString('fr-FR', { maximumFractionDigits: 8 })}</strong>
					and moves the PRUM to <strong>{money(result.buy.new_prum)}</strong>.
				</p>
			{/if}

			{#if result.target}
				{#if result.target.reachable}
					<p>
						To bring the PRUM down to <strong>{money(result.target.target_prum)}</strong>, buy
						<strong
							>{result.target.quantity?.toLocaleString('fr-FR', { maximumFractionDigits: 8 })}</strong
						>
						, that is <strong>{money(result.target.amount)}</strong>.
					</p>
				{:else}
					<p class="text-amber-600">
						A PRUM of {money(result.target.target_prum)} cannot be reached by buying:
						{result.target.reason}.
					</p>
				{/if}
			{/if}
		</div>
	{/if}
</div>
