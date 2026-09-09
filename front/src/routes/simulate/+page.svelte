<script lang="ts">
	import {
		parsePortfolioCsv,
		allocate,
		type Assignment,
		type EnvelopeInput,
		type PlanEnvelope,
		type Row
	} from '$lib/simulate';
	import { Button } from '$lib/components/ui/button/index.js';
	import { formatMoney } from '$lib/utils';
	import { toggleMode } from 'mode-watcher';
	import SunIcon from '@lucide/svelte/icons/sun';
	import MoonIcon from '@lucide/svelte/icons/moon';

	let csv = $state('');
	let fileName = $state('');
	let dragging = $state(false);
	let rows = $state<Row[]>([]);
	let envelopes = $state<EnvelopeInput[]>([{ name: 'PEA', monthly: 300 }]);
	let assign = $state<Record<string, { envelope: string; weight: number }>>({});
	let plan = $state<PlanEnvelope[] | null>(null);
	let error = $state('');
	let fileInput = $state<HTMLInputElement | null>(null);

	function ingest(text: string) {
		csv = text;
		plan = null;
		const result = parsePortfolioCsv(text);
		if ('error' in result) {
			error = result.error;
			rows = [];
			return;
		}
		error = '';
		rows = result.rows;
		const first = envelopes[0]?.name ?? 'PEA';
		const next: Record<string, { envelope: string; weight: number }> = {};
		for (const row of rows) next[row.isin] = assign[row.isin] ?? { envelope: first, weight: 1 };
		assign = next;
	}

	function load(file: File | undefined) {
		if (!file) return;
		fileName = file.name;
		file.text().then(ingest);
	}

	function onDrop(event: DragEvent) {
		event.preventDefault();
		dragging = false;
		load(event.dataTransfer?.files?.[0]);
	}

	// Renaming or removing an envelope would orphan the lines filed under it,
	// and they would vanish from the result. Re-home them on the first one.
	$effect(() => {
		const names = envelopes.filter((e) => e.name.trim()).map((e) => e.name.trim().toUpperCase());
		if (!names.length) return;
		for (const isin of Object.keys(assign)) {
			if (!names.includes(assign[isin].envelope)) assign[isin].envelope = names[0];
		}
	});

	function addEnvelope() {
		envelopes = [...envelopes, { name: '', monthly: 0 }];
	}
	function removeEnvelope(index: number) {
		envelopes = envelopes.filter((_, i) => i !== index);
	}

	function compute() {
		if (!rows.length) {
			error = 'Add a portfolio CSV.';
			return;
		}
		const named = envelopes.filter((e) => e.name.trim());
		if (!named.length) {
			error = 'Name at least one envelope.';
			return;
		}
		error = '';
		const assignments: Assignment[] = rows.map((r) => ({
			isin: r.isin,
			envelope: (assign[r.isin]?.envelope ?? named[0].name).trim().toUpperCase(),
			weight: assign[r.isin]?.weight ?? 1
		}));
		plan = allocate(
			rows,
			named.map((e) => ({ name: e.name.trim().toUpperCase(), monthly: Number(e.monthly) || 0 })),
			assignments
		);
	}

	const total = $derived(
		(plan ?? []).reduce((sum, e) => sum + e.assets.reduce((s, a) => s + a.amount, 0), 0)
	);

	function multLabel(m: number): string {
		return m > 1 ? '×1.5' : m < 1 ? '×0.5' : '×1';
	}
	function multClass(m: number): string {
		if (m > 1) return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300';
		if (m < 1) return 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300';
		return 'text-muted-foreground bg-muted';
	}
</script>

<svelte:head>
	<title>Allocation simulator</title>
</svelte:head>

<div class="mx-auto max-w-3xl px-6 py-10">
	<header class="mb-6 flex items-start justify-between gap-4">
		<div>
			<p class="text-primary mb-1 font-mono text-xs uppercase tracking-widest">allot · simulator</p>
			<h1 class="text-3xl font-bold tracking-tight">Split this month's savings</h1>
			<p class="text-muted-foreground mt-2 max-w-prose">
				Drop a portfolio export, describe your envelopes and their monthly amount. Each envelope
				is shared across its lines, topping up whatever sits below its cost basis.
			</p>
		</div>
		<Button onclick={toggleMode} variant="outline" size="icon" class="shrink-0">
			<SunIcon class="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 !transition-all dark:scale-0 dark:-rotate-90" />
			<MoonIcon class="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 !transition-all dark:scale-100 dark:rotate-0" />
			<span class="sr-only">Theme</span>
		</Button>
	</header>

	<div class="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-600/30 bg-emerald-50 px-3 py-1.5 text-sm text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
		<svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></svg>
		Everything runs in your browser; no data is sent anywhere.
	</div>

	<section class="space-y-4">
		<button
			type="button"
			onclick={() => fileInput?.click()}
			ondragover={(e) => {
				e.preventDefault();
				dragging = true;
			}}
			ondragleave={() => (dragging = false)}
			ondrop={onDrop}
			class="flex w-full cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors {dragging
				? 'border-primary bg-primary/5'
				: 'border-input hover:border-primary/60 hover:bg-muted/40'}"
		>
			<svg class="text-muted-foreground mb-1 h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12" /><path d="m8 7 4-4 4 4" /><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" /></svg>
			{#if fileName}
				<span class="text-sm font-medium">{fileName} · {rows.length} line{rows.length > 1 ? 's' : ''}</span>
				<span class="text-muted-foreground text-xs">Click or drop to replace</span>
			{:else}
				<span class="text-sm font-medium">Drop your CSV here, or click to browse</span>
				<span class="text-muted-foreground text-xs">your broker's portfolio export</span>
			{/if}
		</button>
		<input
			bind:this={fileInput}
			type="file"
			accept=".csv,text/csv,text/plain"
			onchange={(e) => load((e.currentTarget as HTMLInputElement).files?.[0])}
			class="hidden"
		/>
		<details class="text-sm">
			<summary class="text-muted-foreground hover:text-foreground cursor-pointer text-xs uppercase">Or paste the content</summary>
			<textarea
				value={csv}
				oninput={(e) => ingest((e.currentTarget as HTMLTextAreaElement).value)}
				rows="4"
				placeholder="name;isin;quantity;buyingPrice;lastPrice..."
				class="border-input bg-background mt-2 w-full rounded-md border px-3 py-2 font-mono text-xs"
			></textarea>
		</details>

		<div class="rounded-xl border p-4">
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide">Envelopes</h2>
			<div class="space-y-2">
				{#each envelopes as envelope, index (index)}
					<div class="flex items-center gap-2">
						<input bind:value={envelope.name} placeholder="PEA" class="border-input bg-background h-9 w-40 rounded-md border px-3 text-sm uppercase" />
						<div class="relative">
							<input type="number" min="0" bind:value={envelope.monthly} class="border-input bg-background h-9 w-32 rounded-md border px-3 pr-7 text-sm tabular-nums" />
							<span class="text-muted-foreground pointer-events-none absolute right-3 top-1.5 text-sm">€</span>
						</div>
						<span class="text-muted-foreground text-xs">/ mois</span>
						{#if envelopes.length > 1}
							<button type="button" onclick={() => removeEnvelope(index)} class="text-muted-foreground hover:text-foreground ml-1 text-lg leading-none" aria-label="Remove">×</button>
						{/if}
					</div>
				{/each}
			</div>
			<Button variant="outline" size="sm" class="mt-3" onclick={addEnvelope}>Add an envelope</Button>
		</div>

		{#if rows.length > 0}
			<div class="rounded-xl border p-4">
				<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide">Allocation</h2>
				<div class="overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr class="text-muted-foreground text-left text-xs uppercase">
								<th class="py-1 pr-3 font-medium">Asset</th>
								<th class="py-1 pr-3 font-medium">Envelope</th>
								<th class="py-1 font-medium">Weight</th>
							</tr>
						</thead>
						<tbody>
							{#each rows as row (row.isin)}
								<tr class="border-t">
									<td class="max-w-[16rem] truncate py-1.5 pr-3">
										<span class="font-mono text-xs">{row.isin}</span>
										<span class="text-muted-foreground ml-2">{row.name}</span>
									</td>
									<td class="py-1.5 pr-3">
										<select bind:value={assign[row.isin].envelope} class="border-input bg-background h-8 rounded-md border px-2 text-sm">
											{#each envelopes.filter((e) => e.name.trim()) as e (e.name)}
												<option value={e.name.trim().toUpperCase()}>{e.name.trim().toUpperCase()}</option>
											{/each}
										</select>
									</td>
									<td class="py-1.5">
										<input type="number" min="0" step="0.1" bind:value={assign[row.isin].weight} class="border-input bg-background h-8 w-20 rounded-md border px-2 text-sm tabular-nums" />
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{/if}

		<Button onclick={compute} class="w-full">Compute the split</Button>

		{#if error}
			<p class="text-sm text-red-600">{error}</p>
		{/if}

		{#if plan}
			<div class="rounded-xl border p-4">
				<div class="mb-4 flex items-baseline justify-between">
					<h2 class="text-sm font-semibold uppercase tracking-wide">To invest this month</h2>
					<span class="text-lg font-semibold tabular-nums">{formatMoney(total, 'EUR', 0)}</span>
				</div>
				<div class="space-y-4">
					{#each plan as envelope (envelope.name)}
						{@const buying = envelope.assets.filter((a) => a.amount > 0)}
						<div>
							<div class="mb-1 flex items-baseline justify-between">
								<span class="font-semibold">{envelope.name}</span>
								<span class="text-muted-foreground text-sm tabular-nums">{formatMoney(envelope.budget, 'EUR', 0)}</span>
							</div>
							{#if buying.length}
								<ul class="divide-y rounded-md border">
									{#each buying as asset (asset.isin)}
										<li class="flex items-center justify-between gap-3 px-3 py-1.5 text-sm">
											<span class="flex min-w-0 items-center gap-2">
												<span class="truncate">{asset.symbol}</span>
												<span class="rounded px-1.5 py-0.5 font-mono text-xs {multClass(asset.multiplier)}">{multLabel(asset.multiplier)}</span>
												{#if asset.price === null}
													<span class="text-amber-600 text-xs">no quote</span>
												{/if}
											</span>
											<span class="shrink-0 tabular-nums">{formatMoney(asset.amount, 'EUR')}</span>
										</li>
									{/each}
								</ul>
							{:else}
								<p class="text-muted-foreground text-sm">Nothing to invest: no weighted asset.</p>
							{/if}
						</div>
					{/each}
				</div>
				<p class="text-muted-foreground mt-4 text-xs">
					×1.5 when more than 10% below the cost basis (top up), ×0.5 above it (ease off), ×1 otherwise.
				</p>
			</div>
		{/if}
	</section>
</div>
