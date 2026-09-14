<script lang="ts">
	/**
	 * A one-line label that shows itself in full when the column cuts it off.
	 *
	 * The overflow is measured on the element and re-measured when it is
	 * resized, so a name that already fits never puts an overlay on screen and
	 * a narrowed window brings it back. The `title` stays for the browser's own
	 * tooltip and for anything reading the page.
	 */
	let { text, class: className = '' }: { text: string; class?: string } = $props();

	let span = $state<HTMLElement | null>(null);
	let clipped = $state(false);

	$effect(() => {
		// Re-read when the text changes, not only when the box does.
		text;
		if (!span) return;
		const measure = () => (clipped = span!.scrollWidth > span!.clientWidth);
		measure();
		const observer = new ResizeObserver(measure);
		observer.observe(span);
		return () => observer.disconnect();
	});
</script>

<span class="group relative inline-flex min-w-0">
	<span bind:this={span} title={text} class="truncate {className}">{text}</span>
	{#if clipped}
		<span
			class="bg-popover text-popover-foreground pointer-events-none absolute top-full left-0 z-20
				mt-1 hidden max-w-[min(24rem,80vw)] rounded-md border px-2 py-1 text-xs whitespace-nowrap
				shadow-md group-hover:block"
		>
			{text}
		</span>
	{/if}
</span>
