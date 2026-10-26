<script lang="ts">
	import { page } from '$app/state';
	import ShieldCheckIcon from '@lucide/svelte/icons/shield-check';

	import { bookmarkletHref, launcherCode } from '#lib/sources/bookmarklet.js';
	import * as afer from '#lib/sources/afer.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';

	// Built for this very instance: the bookmark sends the reading back here.
	const href = $derived(bookmarkletHref(afer, page.url.origin));
	let copied = $state(false);
	let clickedHere = $state(false);

	// Fallback when Afer's browser policy blocks bookmarks: the same code,
	// pasted into the DevTools console of the Afer tab.
	async function copyForConsole() {
		await navigator.clipboard.writeText(launcherCode(afer, page.url.origin));
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}
</script>

<Dialog.Root>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="outline" size="sm" title="Afer">
				<ShieldCheckIcon class="size-4" />
				<span class="sr-only">Afer</span>
			</Button>
		{/snippet}
	</Dialog.Trigger>

	<Dialog.Content class="sm:max-w-xl">
		<Dialog.Header>
			<Dialog.Title>Import from Afer</Dialog.Title>
			<Dialog.Description>
				Afer has no way to let Allot log in, so the reading happens in your own browser, on the Afer
				site, once you are logged in there. Your Afer credentials never reach Allot.
			</Dialog.Description>
		</Dialog.Header>

		<ol class="list-inside list-decimal space-y-2 text-sm">
			<li>
				Drag this link to your bookmarks bar, once:
				<!-- Clicking it here does nothing useful: it reads Afer's pages. -->
				<a
					{href}
					onclick={(event) => {
						event.preventDefault();
						clickedHere = true;
					}}
					class="bg-primary text-primary-foreground ml-1 inline-block rounded-md px-2 py-0.5 font-medium"
				>
					Allot ← Afer
				</a>
			</li>
			<li>
				Log into your
				<a
					href="https://adherent.gie-afer.fr/"
					target="_blank"
					rel="noreferrer"
					class="underline underline-offset-2">Afer member area</a
				>.
			</li>
			<li>
				Click the bookmark there. Allot opens in a new tab with what it read, and imports it once
				you have checked it. Allow pop-ups on the Afer site if the browser asks.
			</li>
		</ol>

		{#if clickedHere}
			<p class="text-sm text-amber-600">Drag it to the bookmarks bar, then click it on Afer.</p>
		{/if}

		<p class="text-muted-foreground text-xs">
			Nothing happens when you click the bookmark on Afer? Open the browser console on the Afer tab
			and paste this instead:
			<Button variant="ghost" size="sm" class="h-6 px-2 text-xs" onclick={copyForConsole}>
				{copied ? 'Copied' : 'Copy the code'}
			</Button>
		</p>
	</Dialog.Content>
</Dialog.Root>
