<script lang="ts">
	import { getFeedUrl, getNote } from '$lib/services/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';

	let open = $state(false);
	let note = $state('');
	let feed = $state('');
	let hasToken = $state(false);
	let copied = $state('');
	let error = $state('');

	// Loaded when the dialog opens, so the note reflects prices at that moment.
	async function load() {
		error = '';
		try {
			note = await getNote();
			const url = await getFeedUrl();
			feed = url.url;
			hasToken = url.token;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load the note.';
		}
	}

	$effect(() => {
		if (open) load();
	});

	async function copy(what: 'note' | 'feed') {
		try {
			await navigator.clipboard.writeText(what === 'note' ? note : feed);
			copied = what;
			setTimeout(() => (copied = ''), 2000);
		} catch {
			error = 'Clipboard access was denied.';
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="outline" size="sm">Monthly note</Button>
		{/snippet}
	</Dialog.Trigger>

	<Dialog.Content class="max-w-3xl">
		<Dialog.Header>
			<Dialog.Title>Monthly note</Dialog.Title>
			<Dialog.Description>
				Recomputed from current prices. Paste it into a reminder, or subscribe a calendar to the
				feed once - it carries twelve months and rebuilds itself on every fetch.
			</Dialog.Description>
		</Dialog.Header>

		{#if error}
			<p class="text-sm text-red-600">{error}</p>
		{/if}

		<pre
			class="bg-muted max-h-[60vh] overflow-auto rounded p-3 font-mono text-xs leading-relaxed">{note}</pre>

		{#if feed && !hasToken}
			<p class="text-muted-foreground text-xs">
				No ALLOT_FEED_TOKEN is set: a calendar reaching this address without a session gets nothing
				once a password is configured.
			</p>
		{/if}

		<Dialog.Footer>
			<Button variant="outline" onclick={() => copy('feed')} disabled={!feed}>
				{copied === 'feed' ? 'Copied' : 'Copy feed link'}
			</Button>
			<Button onclick={() => copy('note')} disabled={!note}>
				{copied === 'note' ? 'Copied' : 'Copy note'}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
