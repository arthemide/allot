<script lang="ts">
	import { onMount } from 'svelte';
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';

	import { importPreview, importSource } from '#lib/services/api.js';
	import { READING, READY, type SourceSnapshot } from '#lib/sources/bookmarklet.js';
	import { BROWSER_SOURCES, readsFrom } from '#lib/sources/index.js';
	import { decode, prum, validate } from '#lib/sources/payload.js';
	import type { ImportReport, PendingChoices } from '#lib/types/api.js';
	import ImportReportView from '#lib/components/ImportReportView.svelte';
	import LineTickers, { mappings, prefilled } from '#lib/components/LineTickers.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { formatMoney } from '#lib/utils.js';

	// A reading handed over by a source's bookmark, posted by the tab that
	// opened this one. Nothing is written until the user has answered what is
	// new and clicked Import: any site can open this page and post to it.
	let snapshot = $state<SourceSnapshot | null>(null);
	let choices = $state<PendingChoices | null>(null);
	let report = $state<ImportReport | null>(null);
	let error = $state('');
	let busy = $state(false);

	// Envelope typed for each new account (empty leaves it out), ticker for
	// each new line. Both are remembered for the next imports. A line left
	// blank is asked again; leaving it out is a choice of its own.
	let envelopes = $state<Record<string, string>>({});
	let symbols = $state<Record<string, string>>({});
	let excluded = $state<Record<string, boolean>>({});

	// Opened by a bookmark click: say so, and the reading comes by postMessage.
	let waiting = $state(false);

	onMount(() => {
		const fragment = page.url.hash;
		if (fragment.length > 1) {
			// The fallback, when the source's site cuts this tab off from it.
			try {
				const read = decode(fragment);
				if (!(read.source in BROWSER_SOURCES)) {
					throw new Error(`${read.source} is not read in the browser: nothing to import.`);
				}
				receive(read);
			} catch (e) {
				error = e instanceof Error ? e.message : 'The reading could not be read.';
			}
		}
		if (fragment) replaceState(page.url.pathname, {});
		if (snapshot || !window.opener) return;

		function onMessage(event: MessageEvent) {
			if (event.source !== window.opener || event.data?.type !== READING) return;
			try {
				const posted = validate(event.data.snapshot);
				// Any page that opens this one can post to it: only the source's
				// own site may hand over its reading.
				if (!readsFrom(posted.source, event.origin)) {
					throw new Error(`This reading of ${posted.source} did not come from its site.`);
				}
				receive(posted);
			} catch (e) {
				error = e instanceof Error ? e.message : 'The reading could not be read.';
			}
			waiting = false;
			removeEventListener('message', onMessage);
		}
		addEventListener('message', onMessage);
		waiting = true;
		// The opener's origin is unknown here, and "ready" carries nothing.
		window.opener.postMessage({ type: READY }, '*');
		return () => removeEventListener('message', onMessage);
	});

	async function receive(reading: SourceSnapshot) {
		snapshot = reading;
		try {
			choices = await importPreview(reading);
			envelopes = Object.fromEntries(choices.accounts.map((a) => [a.account, a.envelope ?? '']));
			symbols = prefilled(choices.lines);
			excluded = {};
		} catch (e) {
			error = e instanceof Error ? e.message : 'Allot could not check the reading.';
		}
	}

	// A line of a new account left out needs no ticker.
	const leftOut = (account: string) => account in envelopes && !envelopes[account].trim();

	async function run(event: SubmitEvent) {
		event.preventDefault();
		if (!snapshot || !choices) return;
		error = '';
		busy = true;
		try {
			report = await importSource(
				snapshot,
				Object.entries(envelopes).map(([account, name]) => ({
					account,
					// As typed: the offered default is an existing envelope, case included.
					envelope: name.trim() || null
				})),
				mappings(
					choices.lines.filter((line) => !leftOut(line.account)),
					symbols,
					excluded
				)
			);
		} catch (e) {
			error = e instanceof Error ? e.message : 'The import failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Allot - Import</title></svelte:head>

<nav class="flex items-center justify-between border-b px-6 py-3">
	<a href="/" class="hover:text-primary text-sm font-semibold">Allot</a>
	<span class="text-muted-foreground text-sm">Import</span>
</nav>

<main class="mx-auto max-w-5xl space-y-6 px-6 py-6">
	{#if !snapshot}
		{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
		<p class="text-muted-foreground text-sm">
			{waiting
				? 'Waiting for the reading: it comes from the tab you clicked the bookmark in.'
				: "Nothing to import. Click a source's bookmark on its site."}
		</p>
	{:else if report}
		<section class="space-y-3 rounded-lg border p-4">
			<h2 class="font-semibold">Imported from {snapshot.source}</h2>
			<ImportReportView {report} />
			<Button href="/">Back to the overview</Button>
		</section>
	{:else}
		<p class="text-sm">
			Read from {snapshot.source} on {snapshot.read_on}: {snapshot.accounts.length} account{snapshot
				.accounts.length === 1
				? ''
				: 's'}.
		</p>

		<!-- Keyed by position: nothing guarantees a site names two lines apart. -->
		{#each snapshot.accounts as account, a (a)}
			<section class="space-y-2 rounded-lg border p-4">
				<header class="flex flex-wrap items-baseline justify-between gap-2">
					<h2 class="font-semibold">{account.label}</h2>
					<span class="text-muted-foreground text-sm">
						{account.product || 'unknown'} - {formatMoney(account.balance, 'EUR')}
					</span>
				</header>
				{#if account.lines && account.lines.length > 0}
					<table class="w-full text-sm">
						<thead class="text-muted-foreground text-left text-xs uppercase">
							<tr>
								<th class="py-1 pr-3">Fund</th>
								<th class="py-1 pr-3 text-right">Units</th>
								<th class="py-1 pr-3 text-right">Value</th>
								<th class="py-1 text-right">PRUM</th>
							</tr>
						</thead>
						<tbody class="divide-y tabular-nums">
							{#each account.lines as line, l (l)}
								<tr>
									<td class="py-1 pr-3">{line.label}</td>
									<td class="py-1 pr-3 text-right">{line.quantity ?? '-'}</td>
									<td class="py-1 pr-3 text-right">
										{formatMoney(line.valuation, line.currency ?? 'EUR')}
									</td>
									<td class="py-1 text-right">{formatMoney(prum(line), line.currency ?? 'EUR')}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<p class="text-sm text-amber-600">No line.</p>
				{/if}
			</section>
		{/each}

		{#if choices}
			<form class="space-y-4 rounded-lg border p-4" onsubmit={run}>
				{#if choices.accounts.length}
					<div class="space-y-2">
						<p class="text-sm">
							Pick the envelope each new account goes into; it is remembered for the next imports.
							Leave it empty to keep an account out of Allot.
						</p>
						{#each choices.accounts as choice (choice.account)}
							<label class="block space-y-1 text-sm">
								<span>{choice.account} ({choice.lines} line{choice.lines === 1 ? '' : 's'})</span>
								<Input bind:value={envelopes[choice.account]} placeholder="Left out" />
							</label>
						{/each}
					</div>
				{/if}

				{#if choices.lines.some((line) => !leftOut(line.account))}
					<LineTickers
						lines={choices.lines.filter((line) => !leftOut(line.account))}
						bind:symbols
						bind:excluded
					/>
				{/if}

				<p class="text-muted-foreground text-xs">
					Each imported fund's position is set to what the source reports, and a fund it mapped
					before but no longer reports is zeroed. The trades you recorded are kept, and the other
					assets of the envelopes are left alone.
				</p>
				{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
				<Button type="submit" disabled={busy}>{busy ? 'Importing…' : 'Import into Allot'}</Button>
			</form>
		{:else if error}
			<p class="text-destructive text-sm">{error}</p>
		{/if}
	{/if}
</main>
