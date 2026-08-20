<script lang="ts">
	import { getNote } from '$lib/services/api';
	import { Button } from '$lib/components/ui/button/index.js';

	let note = $state('');
	let copied = $state(false);
	let error = $state('');

	$effect(() => {
		getNote()
			.then((text) => (note = text))
			.catch((e) => (error = e instanceof Error ? e.message : 'Could not load the note.'));
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

<div class="space-y-3 rounded-lg border p-4">
	<div class="flex items-center justify-between">
		<h2 class="font-semibold">Monthly note</h2>
		<Button variant="outline" size="sm" onclick={copy} disabled={!note}>
			{copied ? 'Copied' : 'Copy'}
		</Button>
	</div>

	{#if error}
		<p class="text-sm text-red-600">{error}</p>
	{/if}

	<pre class="bg-muted overflow-x-auto rounded p-3 font-mono text-xs leading-relaxed">{note}</pre>

	<p class="text-muted-foreground text-xs">
		Paste it into your own monthly reminder. The app never creates events.
	</p>
</div>
