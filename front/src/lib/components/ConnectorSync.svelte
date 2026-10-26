<script lang="ts">
	import { connectorAccounts, connectorAnswer, connectorLogin } from '#lib/services/api.js';
	import { refresh } from '#lib/state/refresh.svelte.js';
	import type { ConnectorStatus, ImportReport } from '#lib/types/api.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import ImportReportView from '#lib/components/ImportReportView.svelte';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import LandmarkIcon from '@lucide/svelte/icons/landmark';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';

	// The login runs on the server; nothing is kept here. This dialog only
	// carries the credentials through, shows the one second factor the bank
	// asks, and asks where a new account goes.
	let open = $state(false);
	let login = $state('');
	let password = $state('');
	let code = $state('');
	// Envelope typed for each new account; empty leaves the account out.
	let envelopes = $state<Record<string, string>>({});

	let busy = $state(false);
	let error = $state('');
	let status = $state<ConnectorStatus | null>(null);
	let report = $state<ImportReport | null>(null);
	const waitingForUser = $derived(status !== null && status.status !== 'done');

	$effect(() => {
		if (open || waitingForUser || busy) return;
		// Clear everything on close: credentials never linger in memory.
		login = password = code = error = '';
		envelopes = {};
		status = report = null;
	});

	function done(result: ConnectorStatus) {
		status = result;
		if (result.status === 'accounts') {
			envelopes = Object.fromEntries(
				result.accounts.map((choice) => [choice.account, choice.envelope ?? ''])
			);
		}
		if (result.status === 'done') {
			report = result.report;
			refresh.bump();
		}
	}

	async function start(event: SubmitEvent) {
		event.preventDefault();
		if (!login.trim() || !password) {
			error = 'Login and password are both needed.';
			return;
		}
		error = '';
		busy = true;
		try {
			done(await connectorLogin(login.trim(), password));
			password = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'The login failed.';
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
			error = e instanceof Error ? e.message : 'The validation failed.';
			// A failed bank challenge invalidates its server-side attempt. Return to
			// the credentials form instead of offering a dead challenge again.
			status = null;
		} finally {
			busy = false;
		}
	}

	async function place(event: SubmitEvent) {
		event.preventDefault();
		if (!status) return;
		error = '';
		busy = true;
		try {
			const chosen = Object.fromEntries(
				Object.entries(envelopes).map(([account, name]) => [
					account,
					name.trim() ? name.trim().toUpperCase() : null
				])
			);
			done(await connectorAccounts(status.session_id, chosen));
		} catch (e) {
			error = e instanceof Error ? e.message : 'The sync failed.';
			status = null;
		} finally {
			busy = false;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Trigger>
		{#snippet child({ props })}
			{@const label = busy
				? 'BoursoBank - sync in progress'
				: waitingForUser
					? 'BoursoBank - action needed'
					: 'BoursoBank'}
			<Button
				{...props}
				variant={waitingForUser ? 'default' : 'outline'}
				size="sm"
				class="relative"
				title={label}
			>
				{#if busy}
					<LoaderCircle class="size-4 animate-spin" />
				{:else}
					<LandmarkIcon class="size-4" />
				{/if}
				{#if waitingForUser}
					<!-- The logo alone no longer says it: a dot does, as "!" did. -->
					<span
						class="bg-destructive ring-background absolute -top-1 -right-1 size-2.5 rounded-full ring-2"
						aria-hidden="true"
					></span>
				{/if}
				<span class="sr-only">{label}</span>
			</Button>
		{/snippet}
	</Dialog.Trigger>

	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>BoursoBank</Dialog.Title>
			<Dialog.Description>
				The login runs on the server; your login and password are neither stored nor logged. The
				bank is authoritative: each account's positions replace what is tracked here, and the
				trades you recorded are kept.
			</Dialog.Description>
		</Dialog.Header>

		{#if report}
			<ImportReportView {report} />
			{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
			<Dialog.Footer>
				<Button onclick={() => (open = false)}>Close</Button>
			</Dialog.Footer>
		{:else if status && status.status === 'accounts'}
			<form class="space-y-3" onsubmit={place}>
				<p class="text-sm">
					{status.accounts.length === 1 ? 'This account is' : 'These accounts are'} new. Pick the envelope
					each one syncs into; it is remembered for the next syncs. Leave it empty to keep an account
					out of Allot.
				</p>
				{#each status.accounts as choice (choice.account)}
					<div class="space-y-1">
						<Label for="sync-account-{choice.account}">
							{choice.account} ({choice.lines} line{choice.lines === 1 ? '' : 's'})
						</Label>
						<Input
							id="sync-account-{choice.account}"
							bind:value={envelopes[choice.account]}
							placeholder="Left out"
						/>
					</div>
				{/each}
				{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
				<Dialog.Footer>
					<Button type="submit" disabled={busy}>Import</Button>
				</Dialog.Footer>
			</form>
		{:else if status && status.status !== 'done'}
			<form class="space-y-3" onsubmit={answer}>
				<p class="text-sm">{status.prompt}</p>
				{#if status.status === 'otp'}
					<div class="space-y-1">
						<Label for="sync-code">Code received</Label>
						<Input id="sync-code" bind:value={code} autocomplete="one-time-code" />
					</div>
				{/if}
				{#if error}<p class="text-destructive text-sm">{error}</p>{/if}
				<Dialog.Footer>
					<Button type="submit" disabled={busy}>
						{status.status === 'otp' ? 'Check the code' : 'I validated in the app'}
					</Button>
				</Dialog.Footer>
			</form>
		{:else}
			<form class="space-y-3" onsubmit={start} autocomplete="on">
				<div class="space-y-1">
					<Label for="sync-login">Login</Label>
					<Input id="sync-login" name="username" bind:value={login} autocomplete="username" />
				</div>
				<div class="space-y-1">
					<Label for="sync-pw">Password</Label>
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
					<Button type="submit" disabled={busy}>{busy ? 'Logging in…' : 'Log in'}</Button>
				</Dialog.Footer>
			</form>
		{/if}
	</Dialog.Content>
</Dialog.Root>
