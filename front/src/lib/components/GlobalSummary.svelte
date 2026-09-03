<script lang="ts">
	import {
		clearEnvelopeStart,
		deleteAsset,
		getEnvelopes,
		getSummary,
		setEnvelopeAmount,
		setEnvelopeStart,
		updateAsset
	} from '$lib/services/api';
	import type { Envelope, Position, Summary } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Table from '$lib/components/ui/table/index.js';
	import { formatMoney } from '$lib/utils';

	let {
		positions,
		onChange,
		onSelect
	}: {
		positions: Position[];
		onChange: () => void;
		onSelect: (symbol: string) => void;
	} = $props();

	let summary = $state<Summary | null>(null);
	let envelopes = $state<Envelope[]>([]);
	let error = $state('');
	// Envelope name -> amount being typed, so a half-typed number is not sent.
	let drafts = $state<Record<string, string>>({});

	async function load() {
		try {
			[summary, envelopes] = await Promise.all([getSummary(), getEnvelopes()]);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load totals.';
		}
	}

	$effect(() => {
		positions;
		load();
	});

	const eur = (value: number | null) => formatMoney(value, 'EUR');

	function tone(value: number): string {
		return value >= 0 ? 'text-green-600' : 'text-red-600';
	}

	function percent(value: number | null | undefined): string {
		if (value === null || value === undefined) return '';
		return `${value >= 0 ? '+' : ''}${value.toFixed(1)} %`;
	}

	function assetsOf(envelope: string): Position[] {
		return positions.filter((p) => p.envelope === envelope);
	}

	// Weights are relative: what matters is the share of the envelope total.
	function shareOf(asset: Position): number {
		const total = assetsOf(asset.envelope).reduce((sum, p) => sum + p.weight, 0);
		return total > 0 ? (asset.weight / total) * 100 : 0;
	}

	async function saveAmount(envelope: Envelope) {
		const raw = drafts[envelope.name];
		if (raw === undefined) return;
		const value = Number(raw);
		if (!Number.isFinite(value) || value < 0) return;
		await setEnvelopeAmount(envelope.name, value);
		delete drafts[envelope.name];
		await load();
	}

	async function saveWeight(asset: Position, raw: string) {
		const value = Number(raw);
		if (!Number.isFinite(value) || value < 0) return;
		await updateAsset(asset.symbol, {
			label: asset.label,
			envelope: asset.envelope,
			weight: value
		});
		onChange();
	}

	let editing = $state<Envelope | null>(null);
	let startDate = $state('');
	let startCash = $state('');

	function editCash(envelope: Envelope) {
		editing = envelope;
		startDate = envelope.started_on ?? new Date().toISOString().slice(0, 10);
		startCash = String(envelope.opening_cash ?? 0);
	}

	async function saveCash() {
		if (!editing) return;
		const cash = Number(startCash || '0');
		if (!startDate || !Number.isFinite(cash) || cash < 0) return;
		await setEnvelopeStart(editing.name, { started_on: startDate, opening_cash: cash });
		editing = null;
		await load();
	}

	async function stopTracking() {
		if (!editing) return;
		await clearEnvelopeStart(editing.name);
		editing = null;
		await load();
	}

	async function remove(asset: Position) {
		if (!confirm(`Delete ${asset.symbol} and all its transactions?`)) return;
		await deleteAsset(asset.symbol);
		onChange();
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
					<Table.Head class="w-40 text-right">Monthly / weight</Table.Head>
					<Table.Head class="w-24 text-right">Share</Table.Head>
					<Table.Head class="w-32 text-right">Cash</Table.Head>
					<Table.Head class="text-right">Invested</Table.Head>
					<Table.Head class="text-right">Market value</Table.Head>
					<Table.Head class="text-right">Gain / loss</Table.Head>
					<Table.Head class="w-16"></Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each envelopes as envelope (envelope.name)}
					{@const totals = summary.envelopes.find((e) => e.envelope === envelope.name)}
					<Table.Row class="bg-muted/40 font-medium">
						<Table.Cell class="text-left">{envelope.name}</Table.Cell>
						<Table.Cell class="w-40 text-right">
							<Input
								type="number"
								step="any"
								class="ml-auto h-8 w-28 text-right"
								value={drafts[envelope.name] ?? String(envelope.monthly_amount)}
								oninput={(e) => (drafts[envelope.name] = e.currentTarget.value)}
								onblur={() => saveAmount(envelope)}
							/>
						</Table.Cell>
						<Table.Cell class="text-muted-foreground w-24 text-right text-xs">€ / month</Table.Cell>
						<Table.Cell class="w-32 text-right">
							<button
								type="button"
								class="hover:text-primary tabular-nums hover:underline"
								title={envelope.started_on
									? `Saving since ${envelope.started_on}. Click to recalibrate.`
									: 'Not tracking cash. Click to start.'}
								onclick={() => editCash(envelope)}
							>
								{envelope.available === null ? '—' : eur(envelope.available)}
							</button>
						</Table.Cell>
						<Table.Cell class="text-right tabular-nums">{eur(totals?.invested ?? 0)}</Table.Cell>
						<Table.Cell class="text-right tabular-nums">{eur(totals?.market_value ?? 0)}</Table.Cell>
						<Table.Cell class="text-right tabular-nums {tone(totals?.gain ?? 0)}">
							{eur(totals?.gain ?? 0)}
							<span class="ml-1 text-xs font-normal">{percent(totals?.gain_percent)}</span>
						</Table.Cell>
						<Table.Cell class="w-16"></Table.Cell>
					</Table.Row>

					{#each assetsOf(envelope.name) as asset (asset.symbol)}
						{@const totals2 = summary.envelopes
							.find((e) => e.envelope === envelope.name)
							?.assets.find((a) => a.symbol === asset.symbol)}
						<Table.Row>
							<Table.Cell class="pl-8 text-left">
								<button
									type="button"
									class="hover:text-primary text-left hover:underline"
									onclick={() => onSelect(asset.symbol)}
								>
									<span class="font-mono">{asset.symbol}</span>
									<span class="text-muted-foreground ml-2 text-xs">{asset.label}</span>
								</button>
							</Table.Cell>
							<Table.Cell class="w-40 text-right">
								<Input
									type="number"
									step="any"
									class="ml-auto h-8 w-28 text-right"
									value={asset.weight}
									onblur={(e) => saveWeight(asset, e.currentTarget.value)}
								/>
							</Table.Cell>
							<Table.Cell class="w-24 text-right tabular-nums">
								{shareOf(asset).toFixed(0)} %
							</Table.Cell>
							<Table.Cell class="w-32"></Table.Cell>
							<Table.Cell class="text-right tabular-nums">{eur(totals2?.invested ?? 0)}</Table.Cell>
							<Table.Cell class="text-right tabular-nums">
								{eur(totals2?.market_value ?? 0)}
							</Table.Cell>
							<Table.Cell class="text-right tabular-nums {tone(totals2?.gain ?? 0)}">
								{eur(totals2?.gain ?? 0)}
								<span class="ml-1 text-xs">{percent(totals2?.gain_percent)}</span>
							</Table.Cell>
							<Table.Cell class="w-16 text-right">
								<button
									type="button"
									title="Delete {asset.symbol} and its transactions"
									aria-label="Delete {asset.symbol}"
									class="text-muted-foreground/40 hover:text-destructive px-2 leading-none
										transition-colors"
									onclick={() => remove(asset)}
								>
									&times;
								</button>
							</Table.Cell>
						</Table.Row>
					{/each}
				{/each}
			</Table.Body>
		</Table.Root>
	</div>

	<Dialog.Root open={editing !== null} onOpenChange={(value) => (editing = value ? editing : null)}>
		<Dialog.Content class="max-w-md">
			<Dialog.Header>
				<Dialog.Title>{editing?.name} - cash</Dialog.Title>
				<Dialog.Description>
					What is actually in the envelope, and since when. Everything after that is derived:
					the monthly amount, month by month, minus what was bought. Come back here whenever the
					figure stops matching the statement.
				</Dialog.Description>
			</Dialog.Header>

			<label class="text-sm">
				Cash on that date
				<Input type="number" step="any" bind:value={startCash} class="mt-1" />
			</label>
			<label class="text-sm">
				Counting from
				<Input type="date" bind:value={startDate} class="mt-1" />
			</label>

			<Dialog.Footer>
				{#if editing?.started_on}
					<Button variant="ghost" onclick={stopTracking}>Stop tracking</Button>
				{/if}
				<Button onclick={saveCash}>Save</Button>
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Root>

	<p class="text-muted-foreground text-xs">
		Weights are relative: only their share of the envelope matters, so 2 / 1 and 0.67 / 0.33 give
		the same split. An envelope with a cash figure spends it on whole shares and carries what is
		left to the next month; one showing a dash simply splits its monthly amount every month.
		Totals are converted to EUR{summary.eur_usd_rate
			? ` at ${summary.eur_usd_rate.toFixed(4)} USD per EUR`
			: ''}; every other figure stays in the asset's own currency.
	</p>
{:else}
	<p class="text-muted-foreground">Loading totals...</p>
{/if}
