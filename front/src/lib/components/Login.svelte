<script lang="ts">
	import { login } from '$lib/services/api';
	import { session } from '$lib/state/session.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';

	let password = $state('');
	let error = $state('');
	let busy = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		busy = true;
		try {
			await login(password);
			password = '';
			session.authenticated = true;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not log in.';
		} finally {
			busy = false;
		}
	}
</script>

<div class="flex min-h-svh items-center justify-center px-6">
	<form class="w-full max-w-xs space-y-4" onsubmit={submit}>
		<div class="space-y-1">
			<h1 class="text-lg font-semibold">Allot</h1>
			<p class="text-muted-foreground text-sm">This instance is password-protected.</p>
		</div>
		<!-- svelte-ignore a11y_autofocus -->
		<Input
			type="password"
			autocomplete="current-password"
			placeholder="Password"
			autofocus
			bind:value={password}
		/>
		{#if error}
			<p class="text-destructive text-sm">{error}</p>
		{/if}
		<Button type="submit" class="w-full" disabled={busy || !password}>
			{busy ? 'Checking...' : 'Log in'}
		</Button>
	</form>
</div>
