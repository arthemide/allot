<script lang="ts">
	import { getNote } from '$lib/services/api';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';

	let open = $state(false);
	let note = $state('');
	let copied = $state(false);
	let error = $state('');

	// Loaded when the dialog opens, so the note reflects prices at that moment
	// rather than whenever the page happened to load.
	async function load() {
		error = '';
		try {
			note = await getNote();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load the note.';
		}
	}

	$effect(() => {
		if (open) load();
	});

	async function copy() {
		try {
			await navigator.clipboard.writeText(note);
			copied = true;
			setTimeout(() => (copied = false), 2000);
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
				Recomputed from current prices. Paste it into your own monthly reminder.
			</Dialog.Description>
		</Dialog.Header>

		{#if error}
			<p class="text-sm text-red-600">{error}</p>
		{/if}

		<pre
			class="bg-muted max-h-[60vh] overflow-auto rounded p-3 font-mono text-xs leading-relaxed">{note}</pre>

		<Dialog.Footer>
			<Button onclick={copy} disabled={!note}>{copied ? 'Copied' : 'Copy'}</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
