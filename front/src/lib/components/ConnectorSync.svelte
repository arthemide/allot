<script lang="ts">
	import {
		connectorAnswer,
		connectorLogin,
		resolveConnector,
		searchTickers
	} from '$lib/services/api';
	import { refresh } from '$lib/state/refresh.svelte';
	import type {
		ConnectorStatus,
		ImportReport,
		SearchHit,
		UnresolvedLine
	} from '$lib/types/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';

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
	let resolving = $state<UnresolvedLine | null>(null);
	let hits = $state<SearchHit[]>([]);
	let searching = $state(false);
	let tickerQuery = $state('');
	const unresolved = $derived(report?.unresolved.length ?? 0);
	const waitingForUser = $derived(
		(status !== null && status.status !== 'done') || unresolved > 0
	);
	const inFlight = $derived(busy || searching);

	$effect(() => {
		if (open || waitingForUser || inFlight) return;
		// Clear everything on close: credentials never linger in memory.
		login = password = code = error = '';
		status = report = resolving = null;
		hits = [];
		tickerQuery = '';
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
			// A failed bank challenge invalidates its server-side attempt. Return to
			// the credentials form instead of offering a dead challenge again.
			status = null;
		} finally {
			busy = false;
		}
	}

	async function findTicker(line: UnresolvedLine) {
		resolving = line;
		hits = [];
		tickerQuery = line.isin;
		await searchTicker();
	}

	async function searchTicker() {
		if (!resolving || !tickerQuery.trim()) return;
		error = '';
		searching = true;
		try {
			hits = (await searchTickers(tickerQuery.trim())).filter(
				(hit) => hit.currency === resolving?.currency
			);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Recherche impossible.';
		} finally {
			searching = false;
		}
	}

	async function resolve(hit: SearchHit) {
		if (!resolving?.account || !resolving.currency) return;
		error = '';
		busy = true;
		try {
			await resolveConnector({
				account: resolving.account,
				isin: resolving.isin,
				symbol: hit.symbol
			});
			report = report && {
				...report,
				unresolved: report.unresolved.filter(
					(line) => line.account !== resolving?.account || line.isin !== resolving?.isin
				)
			};
			resolving = null;
			hits = [];
			refresh.bump();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Résolution impossible.';
		} finally {
			busy = false;
		}
	}
</script>

	<Dialog.Root bind:open>
		<Dialog.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant={waitingForUser ? 'default' : 'outline'} size="sm">
					{#if inFlight}
						<LoaderCircle class="size-4 animate-spin" />
						<span class="sr-only">Synchronisation BoursoBank en cours</span>
					{:else if waitingForUser}
						<span class="bg-background text-foreground flex size-4 items-center justify-center rounded-full text-xs font-bold">!</span>
						Action requise
					{:else}
						Sync BoursoBank
					{/if}
				</Button>
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
			{#if report.unresolved.length}
				<div class="space-y-2 rounded-md border p-3 text-sm">
					<p class="text-muted-foreground">
						Aucune cotation Yahoo dans la devise Bourso n'a été retenue. Choisissez une cotation
						compatible pour chaque ligne.
					</p>
					{#each report.unresolved as line (`${line.account ?? ''}:${line.isin}`)}
						<div class="flex items-center justify-between gap-3">
							<span>{line.name} ({line.isin}) - {line.currency ?? 'devise inconnue'}</span>
							<Button size="sm" variant="outline" onclick={() => findTicker(line)}>
								Choisir un ticker
							</Button>
						</div>
					{/each}
				</div>
			{/if}
			{#if resolving}
				<div class="space-y-2 rounded-md border p-3 text-sm">
					<p>
						Cotation pour {resolving.name} en {resolving.currency}
					</p>
					<form
						class="flex items-end gap-2"
						onsubmit={(event) => {
							event.preventDefault();
							searchTicker();
						}}
					>
						<div class="flex-1 space-y-1">
							<Label for="ticker-search">Nom ou ticker Yahoo</Label>
							<Input id="ticker-search" bind:value={tickerQuery} />
						</div>
						<Button type="submit" variant="outline" disabled={searching}>
							Rechercher
						</Button>
					</form>
					{#if searching}
						<p class="text-muted-foreground">Recherche...</p>
					{:else if hits.length}
						{#each hits as hit (hit.symbol)}
							<div class="flex items-center justify-between gap-3">
								<span>{hit.symbol} - {hit.label}</span>
								<Button size="sm" variant="outline" disabled={busy} onclick={() => resolve(hit)}>
									Utiliser
								</Button>
							</div>
						{/each}
					{:else}
						<p class="text-muted-foreground">
							Aucune cotation Yahoo en {resolving.currency} trouvée pour cet ISIN.
						</p>
					{/if}
				</div>
			{/if}
			{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
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
			<form class="space-y-3" onsubmit={start} autocomplete="on">
				<div class="space-y-1">
					<Label for="sync-login">Identifiant</Label>
					<Input
						id="sync-login"
						name="username"
						bind:value={login}
						autocomplete="username"
					/>
				</div>
				<div class="space-y-1">
					<Label for="sync-pw">Mot de passe</Label>
					<Input
						id="sync-pw"
						name="password"
						type="password"
						bind:value={password}
						autocomplete="current-password"
					/>
				</div>
				{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
				<Dialog.Footer>
					<Button type="submit" disabled={busy}>{busy ? 'Connexion…' : 'Se connecter'}</Button>
				</Dialog.Footer>
			</form>
		{/if}
	</Dialog.Content>
</Dialog.Root>
