<script lang="ts">
	import { toggleMode } from 'mode-watcher';
	import SunIcon from '@lucide/svelte/icons/sun';
	import MoonIcon from '@lucide/svelte/icons/moon';

	import { Button } from '$lib/components/ui/button/index.js';
	import ImportCsv from '$lib/components/ImportCsv.svelte';
	import MonthlyNote from '$lib/components/MonthlyNote.svelte';
	import TickerSearch from '$lib/components/TickerSearch.svelte';
	import { restartDemo } from '$lib/services/demo';
	import { demo } from '$lib/state/demo.svelte';
	import Dashboard from './Dashboard.svelte';

	// The app, written once. /demo mounts this same component over its
	// in-browser backend, so anything added here shows up in both.
</script>

<nav class="flex items-center justify-between border-b px-6 py-3">
	<div class="flex items-center gap-2">
		<!-- In the demo, "/" is the real app: the brand stays where it is. -->
		<a
			href={demo.enabled ? '/demo/' : '/'}
			class="hover:text-primary text-sm font-semibold"
			title="Back to the overview"
		>
			Allot
		</a>
		{#if demo.enabled}
			<span
				class="rounded-full border border-emerald-600/30 bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
				title="Everything runs in your browser; nothing is saved."
			>
				Demo
			</span>
		{/if}
	</div>
	<div class="flex items-center gap-2">
		{#if demo.enabled}
			<!-- The CSV reader is ported; the ticker lookup needs Yahoo. -->
			<ImportCsv />
			<Button variant="ghost" size="sm" onclick={restartDemo}>Reset</Button>
		{:else}
			<TickerSearch />
			<ImportCsv />
		{/if}
		<MonthlyNote />
		<Button onclick={toggleMode} variant="outline" size="icon">
			<SunIcon
				class="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 !transition-all dark:scale-0 dark:-rotate-90"
			/>
			<MoonIcon
				class="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 !transition-all dark:scale-100 dark:rotate-0"
			/>
			<span class="sr-only">Toggle theme</span>
		</Button>
	</div>
</nav>

<Dashboard />
