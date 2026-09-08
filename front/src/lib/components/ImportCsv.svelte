<script lang="ts">
	import { getEnvelopes, importCsv } from '$lib/services/api';
	import { refresh } from '$lib/state/refresh.svelte';
	import type { Envelope, ImportReport } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';

	// Lives in the header, so it fetches what it needs instead of taking props.
	let envelopes = $state<Envelope[]>([]);

	let open = $state(false);
	let envelope = $state('');
	let csv = $state('');
	let fileName = $state('');
	let importing = $state(false);
	let error = $state('');
	let report = $state<ImportReport | null>(null);

	$effect(() => {
		if (!open) return;
		report = null;
		error = '';
		getEnvelopes()
			.then((e) => (envelopes = e))
			.catch(() => {
				/* the dialog still works without the hints */
			});
	});

	function pick(event: Event) {
		const file = (event.currentTarget as HTMLInputElement).files?.[0];
		if (!file) return;
		fileName = file.name;
		// Read here rather than uploaded: the API takes the text as JSON.
		file.text().then((text) => (csv = text));
	}

	async function run(event: SubmitEvent) {
		event.preventDefault();
		if (!envelope.trim()) {
			error = 'Pick an envelope first.';
			return;
		}
		if (!csv.trim()) {
			error = 'Choose a file or paste its content.';
			return;
		}
		error = '';
		importing = true;
		try {
			report = await importCsv(envelope.trim().toUpperCase(), csv);
			refresh.bump();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Import failed.';
		} finally {
			importing = false;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="outline" size="sm">Import a CSV</Button>
		{/snippet}
	</Dialog.Trigger>

	<Dialog.Content class="sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Import a portfolio export</Dialog.Title>
			<Dialog.Description>
				The broker's portfolio CSV, with a quantity and a cost per line - not the account
				movements. Each line becomes the asset's opening position, PRUM included; importing
				again replaces it. Assets already tracked keep their envelope and weight.
			</Dialog.Description>
		</Dialog.Header>

		<form class="space-y-3" onsubmit={run}>
			<div class="flex flex-wrap items-end gap-3">
				<div class="space-y-1">
					<label for="import-file" class="text-muted-foreground block text-xs uppercase">
						File
					</label>
					<input
						id="import-file"
						type="file"
						accept=".csv,text/csv,text/plain"
						onchange={pick}
						class="border-input bg-background h-9 w-64 rounded-md border px-3 py-1.5 text-sm file:mr-2 file:border-0 file:bg-transparent file:text-sm file:font-medium"
					/>
				</div>
				<div class="space-y-1">
					<label for="import-env" class="text-muted-foreground block text-xs uppercase">
						Into envelope
					</label>
					<input
						id="import-env"
						bind:value={envelope}
						list="import-envelope-list"
						placeholder="PEA"
						class="border-input bg-background h-9 w-40 rounded-md border px-3 text-sm"
					/>
					<datalist id="import-envelope-list">
						{#each envelopes as e (e.name)}
							<option value={e.name}></option>
						{/each}
					</datalist>
				</div>
				<Button type="submit" disabled={importing}>{importing ? 'Importing...' : 'Import'}</Button>
			</div>

			<div class="space-y-1">
				<label for="import-text" class="text-muted-foreground block text-xs uppercase">
					{fileName ? `Content of ${fileName}` : 'Or paste the content'}
				</label>
				<textarea
					id="import-text"
					bind:value={csv}
					rows="5"
					placeholder="name;isin;quantity;buyingPrice;..."
					class="border-input bg-background w-full rounded-md border px-3 py-2 font-mono text-xs"
				></textarea>
			</div>
		</form>

		{#if error}
			<p class="text-sm text-red-600">{error}</p>
		{/if}

		{#if report}
			<div class="space-y-2 text-sm">
				<p>
					{report.imported.length} of {report.total} line{report.total === 1 ? '' : 's'} imported.
				</p>
				{#if report.imported.length > 0}
					<ul class="divide-y rounded-md border">
						{#each report.imported as line (line.symbol)}
							<li class="flex items-baseline justify-between gap-3 px-3 py-1.5">
								<span class="min-w-0 truncate">
									<span class="font-mono font-medium">{line.symbol}</span>
									<span class="text-muted-foreground ml-2">{line.label}</span>
								</span>
								<span class="shrink-0 tabular-nums">{line.quantity} @ {line.prum}</span>
							</li>
						{/each}
					</ul>
				{/if}
				{#if report.unresolved.length > 0}
					<p class="text-amber-600">
						No ticker answers to {report.unresolved.length === 1 ? 'this line' : 'these lines'};
						nothing was written for {report.unresolved.length === 1 ? 'it' : 'them'}:
					</p>
					<ul class="text-muted-foreground list-inside list-disc">
						{#each report.unresolved as line (line.isin)}
							<li><span class="font-mono">{line.isin}</span> {line.name}</li>
						{/each}
					</ul>
				{/if}
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
