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
	let dragging = $state(false);
	let error = $state('');
	let report = $state<ImportReport | null>(null);
	let fileInput = $state<HTMLInputElement | null>(null);

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

	function load(file: File | undefined) {
		if (!file) return;
		fileName = file.name;
		error = '';
		// Read here rather than uploaded: the API takes the text as JSON.
		file.text().then((text) => (csv = text));
	}

	function onDrop(event: DragEvent) {
		event.preventDefault();
		dragging = false;
		load(event.dataTransfer?.files?.[0]);
	}

	async function run(event: SubmitEvent) {
		event.preventDefault();
		if (!envelope.trim()) {
			error = 'Pick an envelope first.';
			return;
		}
		if (!csv.trim()) {
			error = 'Drop a file or paste its content.';
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
				Your broker's portfolio CSV, with a quantity and a cost per line - not the account
				movements. Each line becomes the asset's opening position, PRUM included; importing
				again replaces it. Assets already tracked keep their envelope and weight.
			</Dialog.Description>
		</Dialog.Header>

		<form class="space-y-3" onsubmit={run}>
			<!-- The dropzone: click to browse, or drag a file onto it. -->
			<button
				type="button"
				onclick={() => fileInput?.click()}
				ondragover={(e) => {
					e.preventDefault();
					dragging = true;
				}}
				ondragleave={() => (dragging = false)}
				ondrop={onDrop}
				class="flex w-full cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors {dragging
					? 'border-primary bg-primary/5'
					: 'border-input hover:border-primary/60 hover:bg-muted/40'}"
			>
				<svg
					class="text-muted-foreground mb-1 h-6 w-6"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d="M12 3v12" />
					<path d="m8 7 4-4 4 4" />
					<path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" />
				</svg>
				{#if fileName}
					<span class="text-sm font-medium">{fileName}</span>
					<span class="text-muted-foreground text-xs">Click or drop to replace</span>
				{:else}
					<span class="text-sm font-medium">Drop your CSV here, or click to browse</span>
					<span class="text-muted-foreground text-xs">.csv from your broker's portfolio</span>
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
				<summary class="text-muted-foreground hover:text-foreground cursor-pointer text-xs uppercase">
					Or paste the content
				</summary>
				<textarea
					bind:value={csv}
					rows="5"
					placeholder="name;isin;quantity;buyingPrice;..."
					class="border-input bg-background mt-2 w-full rounded-md border px-3 py-2 font-mono text-xs"
				></textarea>
			</details>

			<div class="flex flex-wrap items-end gap-3">
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
				{#if report.elsewhere.length > 0}
					<p class="text-amber-600">
						Already tracked in another envelope; the position was updated but
						{report.elsewhere.length === 1 ? 'it was' : 'they were'} left there:
					</p>
					<ul class="text-muted-foreground list-inside list-disc">
						{#each report.elsewhere as line (line.symbol)}
							<li>
								<span class="font-mono">{line.symbol}</span>
								<span class="ml-1">in {line.envelope}</span>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
