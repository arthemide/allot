<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { ModeWatcher } from "mode-watcher";
	import SunIcon from "@lucide/svelte/icons/sun";
	import MoonIcon from "@lucide/svelte/icons/moon";
	
	import { toggleMode } from "mode-watcher";
	import { Button } from "$lib/components/ui/button/index.js";
	import MonthlyNote from "$lib/components/MonthlyNote.svelte";
	import TickerSearch from "$lib/components/TickerSearch.svelte";
	import Login from "$lib/components/Login.svelte";
	import { getSession } from "$lib/services/api";
	import { session } from "$lib/state/session.svelte";

	let { children } = $props();

	// An instance with no password never shows a login screen.
	$effect(() => {
		getSession()
			.then((state) => {
				session.required = state.required;
				session.authenticated = state.authenticated;
			})
			.catch(() => {
				// Unreachable API: the form is the one thing that might help.
				session.required = true;
				session.authenticated = false;
			})
			.finally(() => (session.ready = true));
	});
</script>

<svelte:head>
	<title>Allot</title>
	<link rel="icon" href={favicon} />
</svelte:head>

<ModeWatcher />

{#if !session.ready}
	<!-- No flash of the app before the answer comes back. -->
{:else if session.required && !session.authenticated}
	<Login />
{:else}
<nav class="flex items-center justify-between border-b px-6 py-3">
	<a href="/" class="hover:text-primary text-sm font-semibold" title="Back to the overview">
		Allot
	</a>
	<div class="flex items-center gap-2">
	<TickerSearch />
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

{@render children()}
{/if}