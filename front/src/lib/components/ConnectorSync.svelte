<script lang="ts">
	import { connectorAnswer, connectorLogin } from '$lib/services/api';
	import { refresh } from '$lib/state/refresh.svelte';
	import type { ConnectorStatus, ImportReport } from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';

	// The login runs on the Pi; nothing is kept here. This dialog only carries
	// the credentials through and shows the one second-factor the bank asks.
	let open = $state(false);
	let login = $state('');
	let password = $state('');
	let code = $state('');

	let busy = $state(false);
	let error = $state('');
	let status = $state<ConnectorStatus | null>(null);
	let report = $state<ImportReport | null>(null);

	$effect(() => {
		if (open) return;
		// Clear everything on close: credentials never linger in memory.
		login = password = code = error = '';
		status = report = null;
		busy = false;
	});

	function done(result: ConnectorStatus) {
		status = result;
		if (result.status === 'done') {
			report = result.report;
			refresh.bump();
		}
	}

	async function start(event: SubmitEvent) {
		event.preventDefault();
		if (!login.trim() || !password) {
			error = 'Identifiant et mot de passe requis.';
			return;
		}
		error = '';
		busy = true;
		try {
			done(await connectorLogin(login.trim(), password));
			password = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Connexion échouée.';
		} finally {
			busy = false;
		}
	}

	async function answer(event: SubmitEvent) {
		event.preventDefault();
		if (!status) return;
		error = '';
		busy = true;
		try {
			done(await connectorAnswer(status.session_id, code.trim()));
			code = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Validation échouée.';
		} finally {
			busy = false;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="outline" size="sm">Sync BoursoBank</Button>
		{/snippet}
	</Dialog.Trigger>

	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Synchroniser BoursoBank</Dialog.Title>
			<Dialog.Description>
				La connexion se fait sur le serveur. Identifiant et mot de passe ne sont ni enregistrés ni
				journalisés. La banque fait foi : les positions du PEA remplacent ce qui est suivi ici.
			</Dialog.Description>
		</Dialog.Header>

		{#if report}
			<p class="text-sm">
				{report.imported.length} ligne(s) importée(s){#if report.unresolved.length},
					{report.unresolved.length} non résolue(s){/if}.
			</p>
			<Dialog.Footer>
				<Button onclick={() => (open = false)}>Fermer</Button>
			</Dialog.Footer>
		{:else if status && status.status !== 'done'}
			<form class="space-y-3" onsubmit={answer}>
				<p class="text-sm">{status.prompt}</p>
				{#if status.status === 'otp'}
					<div class="space-y-1">
						<Label for="sync-code">Code reçu</Label>
						<Input id="sync-code" bind:value={code} autocomplete="one-time-code" />
					</div>
				{/if}
				{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
				<Dialog.Footer>
					<Button type="submit" disabled={busy}>
						{status.status === 'otp' ? 'Valider le code' : "J'ai validé dans l'appli"}
					</Button>
				</Dialog.Footer>
			</form>
		{:else}
			<form class="space-y-3" onsubmit={start}>
				<div class="space-y-1">
					<Label for="sync-login">Identifiant</Label>
					<Input id="sync-login" bind:value={login} autocomplete="off" />
				</div>
				<div class="space-y-1">
					<Label for="sync-pw">Mot de passe</Label>
					<Input id="sync-pw" type="password" bind:value={password} autocomplete="off" />
				</div>
				{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
				<Dialog.Footer>
					<Button type="submit" disabled={busy}>{busy ? 'Connexion…' : 'Se connecter'}</Button>
				</Dialog.Footer>
			</form>
		{/if}
	</Dialog.Content>
</Dialog.Root>
