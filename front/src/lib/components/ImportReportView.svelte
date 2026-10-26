<script lang="ts">
	import type { ImportReport } from '#lib/types/api.js';
	import { formatMoney } from '#lib/utils.js';

	// What a source sync did, whichever source it was: BoursoBank or a browser
	// reading. The CSV import has its own, simpler report.
	let { report }: { report: ImportReport } = $props();

	const conflicts = $derived(report.conflicts ?? []);
	const available = $derived(report.available ?? []);
</script>

<p class="text-sm">
	{report.imported.length} line{report.imported.length === 1 ? '' : 's'} imported{#if report.unresolved.length},
		{report.unresolved.length} unresolved{/if}{#if conflicts.length},
		{conflicts.length} in conflict{/if}.
</p>
{#if report.unresolved.length}
	<div class="space-y-2 rounded-md border p-3 text-sm">
		<p class="text-muted-foreground">
			Nothing was written for these lines: no ticker, no cost price, or no Yahoo listing in the
			source's currency. Add them by hand. Until they are, nothing in their account is zeroed.
		</p>
		<ul class="list-inside list-disc">
			{#each report.unresolved as line, index (index)}
				<li>{line.name}{line.isin ? ` (${line.isin})` : ''}</li>
			{/each}
		</ul>
	</div>
{/if}
{#if conflicts.length}
	<div class="space-y-2 rounded-md border p-3 text-sm">
		<p class="text-muted-foreground">
			The trades recorded here hold more than the source reports, so these lines were left as they
			were. Record the missing sells, then import again.
		</p>
		<ul class="list-inside list-disc">
			{#each conflicts as line (line.symbol)}
				<li>
					<span class="font-mono">{line.symbol}</span>
					{line.label}: {line.tracked_quantity} tracked, {line.bank_quantity} at the source
				</li>
			{/each}
		</ul>
	</div>
{/if}
{#if available.length}
	<div class="space-y-2 rounded-md border p-3 text-sm">
		<p class="text-muted-foreground">
			Held as an amount, without units: no position can carry it, so it is shown and not written.
		</p>
		<ul class="list-inside list-disc tabular-nums">
			{#each available as line, index (index)}
				<li>
					{line.envelope} - {line.label}: {formatMoney(line.value, line.currency)}
				</li>
			{/each}
		</ul>
	</div>
{/if}
