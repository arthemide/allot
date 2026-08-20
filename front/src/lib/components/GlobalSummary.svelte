<script lang="ts">
	import { getSummary } from '$lib/services/api';
	import type { Summary } from '$lib/types/api';
	import * as Table from '$lib/components/ui/table/index.js';
	import { formatMoney } from '$lib/utils';

	let summary = $state<Summary | null>(null);
	let error = $state('');

	$effect(() => {
		getSummary()
			.then((data) => (summary = data))
			.catch((e) => (error = e instanceof Error ? e.message : 'Could not load totals.'));
	});

	const eur = (value: number | null) => formatMoney(value, 'EUR');

	function tone(value: number): string {
		return value >= 0 ? 'text-green-600' : 'text-red-600';
	}
</script>

{#if error}
	<p class="text-red-600">{error}</p>
{:else if summary}
	<div class="grid grid-cols-2 gap-4 rounded-lg border p-4 sm:grid-cols-4">
		<div>
			<div class="text-muted-foreground text-xs uppercase">Invested</div>
			<div class="text-lg font-semibold">{eur(summary.invested)}</div>
		</div>
		<div>
			<div class="text-muted-foreground text-xs uppercase">Market value</div>
			<div class="text-lg font-semibold">{eur(summary.market_value)}</div>
		</div>
		<div>
			<div class="text-muted-foreground text-xs uppercase">Gain / loss</div>
			<div class="text-lg font-semibold {tone(summary.gain)}">{eur(summary.gain)}</div>
		</div>
		<div>
			<div class="text-muted-foreground text-xs uppercase">Performance</div>
			<div class="text-lg font-semibold {tone(summary.gain)}">
				{summary.gain_percent === null
					? '-'
					: `${summary.gain_percent >= 0 ? '+' : ''}${summary.gain_percent.toFixed(2)} %`}
			</div>
		</div>
	</div>

	<div class="rounded-lg border">
		<Table.Root>
			<Table.Header>
				<Table.Row>
					<Table.Head class="text-left">Envelope / asset</Table.Head>
					<Table.Head class="text-right">Invested</Table.Head>
					<Table.Head class="text-right">Market value</Table.Head>
					<Table.Head class="text-right">Gain / loss</Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each summary.envelopes as envelope (envelope.envelope)}
					<Table.Row class="bg-muted/40 font-medium">
						<Table.Cell class="text-left">{envelope.envelope}</Table.Cell>
						<Table.Cell class="text-right tabular-nums">{eur(envelope.invested)}</Table.Cell>
						<Table.Cell class="text-right tabular-nums">{eur(envelope.market_value)}</Table.Cell>
						<Table.Cell class="text-right tabular-nums {tone(envelope.gain)}">
							{eur(envelope.gain)}
						</Table.Cell>
					</Table.Row>
					{#each envelope.assets as asset (asset.symbol)}
						<Table.Row>
							<Table.Cell class="text-muted-foreground pl-8 text-left">{asset.symbol}</Table.Cell>
							<Table.Cell class="text-right tabular-nums">{eur(asset.invested)}</Table.Cell>
							<Table.Cell class="text-right tabular-nums">{eur(asset.market_value)}</Table.Cell>
							<Table.Cell class="text-right tabular-nums {tone(asset.gain)}">
								{eur(asset.gain)}
							</Table.Cell>
						</Table.Row>
					{/each}
				{/each}
			</Table.Body>
		</Table.Root>
	</div>

	<p class="text-muted-foreground text-xs">
		Totals are converted to EUR{summary.eur_usd_rate
			? ` at ${summary.eur_usd_rate.toFixed(4)} USD per EUR`
			: ''}. Every other figure stays in the asset's own currency.
	</p>
{:else}
	<p class="text-muted-foreground">Loading totals...</p>
{/if}
