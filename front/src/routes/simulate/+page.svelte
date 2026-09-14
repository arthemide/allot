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

	function addEnvelope() {
		envelopes = [...envelopes, { name: '', monthly: 0 }];
	}
	function removeEnvelope(index: number) {
		envelopes = envelopes.filter((_, i) => i !== index);
	}

	function compute() {
		if (!rows.length) {
			error = 'Ajoute un CSV de portefeuille.';
			return;
		}
		const named = envelopes.filter((e) => e.name.trim());
		if (!named.length) {
			error = 'Nomme au moins une enveloppe.';
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

	function euro(value: number, decimals = 2): string {
		return value.toLocaleString('fr-FR', {
			minimumFractionDigits: decimals,
			maximumFractionDigits: decimals
		});
	}
	function multLabel(m: number): string {
		return m > 1 ? '×1,5' : m < 1 ? '×0,5' : '×1';
	}
	function multClass(m: number): string {
		if (m > 1) return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300';
		if (m < 1) return 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300';
		return 'text-muted-foreground bg-muted';
	}
</script>

<svelte:head>
	<title>Simulateur d'allocation</title>
</svelte:head>

<div class="mx-auto max-w-3xl px-6 py-10">
	<header class="mb-6 flex items-start justify-between gap-4">
		<div>
			<p class="text-primary mb-1 font-mono text-xs uppercase tracking-widest">allot · simulateur</p>
			<h1 class="text-3xl font-bold tracking-tight">Répartis ton épargne du mois</h1>
			<p class="text-muted-foreground mt-2 max-w-prose">
				Dépose un export de portefeuille, décris tes enveloppes et leur montant mensuel. Chaque
				enveloppe est partagée entre ses lignes, en renforçant ce qui est sous son prix de revient.
			</p>
		</div>
		<Button onclick={toggleMode} variant="outline" size="icon" class="shrink-0">
			<SunIcon class="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 !transition-all dark:scale-0 dark:-rotate-90" />
			<MoonIcon class="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 !transition-all dark:scale-100 dark:rotate-0" />
			<span class="sr-only">Thème</span>
		</Button>
	</header>

	<div class="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-600/30 bg-emerald-50 px-3 py-1.5 text-sm text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
		<svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></svg>
		Tout se calcule dans ton navigateur ; aucune donnée n'est envoyée.
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
				<span class="text-sm font-medium">{fileName} · {rows.length} ligne{rows.length > 1 ? 's' : ''}</span>
				<span class="text-muted-foreground text-xs">Clique ou dépose pour remplacer</span>
			{:else}
				<span class="text-sm font-medium">Dépose ton CSV ici, ou clique pour parcourir</span>
				<span class="text-muted-foreground text-xs">l'export portefeuille de ton courtier</span>
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
			<summary class="text-muted-foreground hover:text-foreground cursor-pointer text-xs uppercase">Ou colle le contenu</summary>
			<textarea
				value={csv}
				oninput={(e) => ingest((e.currentTarget as HTMLTextAreaElement).value)}
				rows="4"
				placeholder="name;isin;quantity;buyingPrice;lastPrice…"
				class="border-input bg-background mt-2 w-full rounded-md border px-3 py-2 font-mono text-xs"
			></textarea>
		</details>

		<div class="rounded-xl border p-4">
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide">Enveloppes</h2>
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
							<button type="button" onclick={() => removeEnvelope(index)} class="text-muted-foreground hover:text-foreground ml-1 text-lg leading-none" aria-label="Retirer">×</button>
						{/if}
					</div>
				{/each}
			</div>
			<Button variant="outline" size="sm" class="mt-3" onclick={addEnvelope}>Ajouter une enveloppe</Button>
		</div>

		{#if rows.length > 0}
			<div class="rounded-xl border p-4">
				<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide">Répartition</h2>
				<div class="overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr class="text-muted-foreground text-left text-xs uppercase">
								<th class="py-1 pr-3 font-medium">Actif</th>
								<th class="py-1 pr-3 font-medium">Enveloppe</th>
								<th class="py-1 font-medium">Poids</th>
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

		<Button onclick={compute} class="w-full">Calculer l'allocation</Button>

		{#if error}
			<p class="text-sm text-red-600">{error}</p>
		{/if}

		{#if plan}
			<div class="rounded-xl border p-4">
				<div class="mb-4 flex items-baseline justify-between">
					<h2 class="text-sm font-semibold uppercase tracking-wide">À placer ce mois</h2>
					<span class="text-lg font-semibold tabular-nums">{euro(total, 0)} €</span>
				</div>
				<div class="space-y-4">
					{#each plan as envelope (envelope.name)}
						{@const buying = envelope.assets.filter((a) => a.amount > 0)}
						<div>
							<div class="mb-1 flex items-baseline justify-between">
								<span class="font-semibold">{envelope.name}</span>
								<span class="text-muted-foreground text-sm tabular-nums">{euro(envelope.budget, 0)} €</span>
							</div>
							{#if buying.length}
								<ul class="divide-y rounded-md border">
									{#each buying as asset (asset.isin)}
										<li class="flex items-center justify-between gap-3 px-3 py-1.5 text-sm">
											<span class="flex min-w-0 items-center gap-2">
												<span class="truncate">{asset.symbol}</span>
												<span class="rounded px-1.5 py-0.5 font-mono text-xs {multClass(asset.multiplier)}">{multLabel(asset.multiplier)}</span>
												{#if asset.price === null}
													<span class="text-amber-600 text-xs">cours absent</span>
												{/if}
											</span>
											<span class="shrink-0 tabular-nums">{euro(asset.amount)} €</span>
										</li>
									{/each}
								</ul>
							{:else}
								<p class="text-muted-foreground text-sm">Rien à placer : aucun actif pondéré.</p>
							{/if}
						</div>
					{/each}
				</div>
				<p class="text-muted-foreground mt-4 text-xs">
					×1,5 sous le prix de revient de plus de 10 % (on renforce), ×0,5 au-dessus (on allège), ×1 sinon.
				</p>
			</div>
		{/if}
	</section>
</div>
