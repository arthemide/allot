<script lang="ts" module>
	import type { PendingLine } from '#lib/types/api.js';

	/**
	 * The answers to send: a ticker, or null to leave the line out. A line left
	 * blank is not sent, so it is asked again.
	 */
	export function mappings(
		lines: PendingLine[],
		symbols: Record<string, string>,
		excluded: Record<string, boolean>
	) {
		return lines
			.filter((line) => excluded[line.label] || symbols[line.label]?.trim())
			.map((line) => ({
				label: line.label,
				symbol: excluded[line.label] ? null : symbols[line.label].trim()
			}));
	}

	/** What each line starts with: its ISIN's listing, never a guess from the label. */
	export function prefilled(lines: PendingLine[]) {
		return Object.fromEntries(lines.map((line) => [line.label, line.found ?? '']));
	}
</script>

<script lang="ts">
	import { searchTickers } from '#lib/services/api.js';
	import type { SearchHit } from '#lib/types/api.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';

	// The ticker of each new line of a source, remembered for the next imports.
	// A guess from the label is only offered: a wrong ticker silently merges
	// two funds.
	let {
		lines,
		symbols = $bindable(),
		excluded = $bindable()
	}: {
		lines: PendingLine[];
		symbols: Record<string, string>;
		excluded: Record<string, boolean>;
	} = $props();

	let hits = $state<Record<string, SearchHit[]>>({});
	let error = $state('');

	async function search(label: string) {
		error = '';
		try {
			hits[label] = (await searchTickers(symbols[label].trim() || label)).slice(0, 5);
		} catch (e) {
			error = e instanceof Error ? e.message : 'The search failed.';
		}
	}
</script>

<div class="space-y-2">
	<p class="text-sm">
		Pick the ticker each line is quoted under; it is remembered for the next imports. A listing found
		from the line's ISIN is filled in: check it, the one you already track may be another. A line
		left blank is asked again next time; meanwhile it is resolved from its ISIN or, without one,
		holds back the zeroing of its envelope.
	</p>
	{#each lines as line (line.label)}
		<div class="space-y-1 text-sm">
			<span>
				{line.label}
				{#if line.isin}<span class="text-muted-foreground font-mono text-xs">{line.isin}</span>{/if}
			</span>
			<div class="flex items-center gap-2">
				<Input
					bind:value={symbols[line.label]}
					placeholder={excluded[line.label] ? 'Left out' : 'Ticker'}
					disabled={excluded[line.label]}
					class="font-mono"
				/>
				<Button
					variant="outline"
					disabled={excluded[line.label]}
					onclick={() => search(line.label)}
				>
					Search
				</Button>
				<label class="text-muted-foreground flex shrink-0 items-center gap-1 text-xs">
					<input type="checkbox" bind:checked={excluded[line.label]} />
					Leave out
				</label>
			</div>
			{#if line.symbol && symbols[line.label] !== line.symbol && !excluded[line.label]}
				<button
					type="button"
					class="text-muted-foreground hover:text-primary text-xs hover:underline"
					onclick={() => (symbols[line.label] = line.symbol ?? '')}
				>
					Maybe <span class="font-mono">{line.symbol}</span>, already tracked? Use it
				</button>
			{/if}
			{#if hits[line.label]?.length}
				<div class="flex flex-wrap gap-1">
					{#each hits[line.label] as hit (hit.symbol)}
						<Button
							variant="ghost"
							size="sm"
							onclick={() => {
								symbols[line.label] = hit.symbol;
								hits[line.label] = [];
							}}
						>
							<span class="font-mono">{hit.symbol}</span>
							<span class="text-muted-foreground">{hit.label}</span>
						</Button>
					{/each}
				</div>
			{:else if hits[line.label]}
				<p class="text-muted-foreground text-xs">No listing found.</p>
			{/if}
		</div>
	{/each}
	{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
</div>
