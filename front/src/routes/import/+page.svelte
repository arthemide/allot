<script lang="ts">
	import { onMount } from 'svelte';
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';

	import { decode } from '#lib/afer/payload.js';
	import type { SourceSnapshot } from '#lib/sources/bookmarklet.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { formatMoney } from '#lib/utils.js';

	let snapshot = $state<SourceSnapshot | null>(null);
	let error = $state('');

	onMount(() => {
		const fragment = page.url.hash;
		try {
			if (fragment.length > 1) snapshot = decode(fragment) as unknown as SourceSnapshot;
		} catch (e) {
			error = e instanceof Error ? e.message : 'The reading could not be read.';
		} finally {
			if (fragment) replaceState(page.url.pathname, {});
		}
	});
</script>

<svelte:head><title>Allot - Import</title></svelte:head>

<nav class="flex items-center justify-between border-b px-6 py-3">
	<a href="/" class="hover:text-primary text-sm font-semibold">Allot</a>
	<span class="text-muted-foreground text-sm">Import</span>
</nav>

<main class="mx-auto max-w-5xl space-y-6 px-6 py-6">
	{#if error}
		<p class="text-sm text-red-600">{error}</p>
	{:else if !snapshot}
		<p class="text-muted-foreground text-sm">Nothing to show. Click a source's bookmark on its site.</p>
	{:else}
		<p class="text-sm">Read on {snapshot.read_on}: {snapshot.accounts.length} account(s).</p>
		{#each snapshot.accounts as account (account.label)}
			<section class="space-y-2 rounded-lg border p-4">
				<header class="flex flex-wrap items-baseline justify-between gap-2">
					<h2 class="font-semibold">{account.label}</h2>
					<span class="text-muted-foreground text-sm">
						{account.product || 'unknown'} - {formatMoney(account.balance ?? null, 'EUR')}
					</span>
				</header>
				{#if account.lines && account.lines.length > 0}
					<table class="w-full text-sm">
						<thead class="text-muted-foreground text-left text-xs uppercase">
							<tr><th class="py-1 pr-3">Fund</th><th class="py-1 pr-3 text-right">Units</th><th class="py-1 pr-3 text-right">Value</th><th class="py-1">PRUM</th></tr>
						</thead>
						<tbody class="divide-y tabular-nums">
							{#each account.lines as line (line.label)}
								<tr>
									<td class="py-1 pr-3">{line.label}</td>
									<td class="py-1 pr-3 text-right">{line.quantity ?? '-'}</td>
									<td class="py-1 pr-3 text-right">{formatMoney(line.valuation ?? null, 'EUR')}</td>
									<td class="py-1">{line.unit_cost ?? (line.invested && line.quantity ? line.invested / line.quantity : '-')}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<p class="text-sm text-amber-600">No line.</p>
				{/if}
			</section>
		{/each}
		<p class="text-muted-foreground text-xs">Preview only - nothing written yet.</p>
	{/if}
</main>
