<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { ModeWatcher } from 'mode-watcher';

	import Login from '$lib/components/Login.svelte';
	import { getSession } from '$lib/services/api';
	import { demo } from '$lib/state/demo.svelte';
	import { session } from '$lib/state/session.svelte';

	let { children } = $props();

	// The demo has no server to ask and no password to hold: it walks
	// straight in. Everything below the login gate is the same app.
	$effect(() => {
		if (demo.enabled) {
			session.ready = true;
			session.required = false;
			session.authenticated = true;
			return;
		}
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
	{@render children()}
{/if}
