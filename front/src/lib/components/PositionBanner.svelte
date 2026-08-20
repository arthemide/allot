<script lang="ts">
	import type { Position } from '$lib/types/api';
	import { formatMoney } from '$lib/utils';

	let { position }: { position: Position } = $props();

	const money = $derived((value: number | null) => formatMoney(value, position.currency));

	function quantity(value: number): string {
		return value.toLocaleString('fr-FR', { maximumFractionDigits: 8 });
	}

	function percent(value: number | null): string {
		if (value === null) return '-';
		return `${value >= 0 ? '+' : ''}${value.toFixed(2)} %`;
	}

	const tone = $derived(
		position.gain === null ? '' : position.gain >= 0 ? 'text-green-600' : 'text-red-600'
	);
</script>

<div class="grid grid-cols-2 gap-4 rounded-lg border p-4 sm:grid-cols-3 lg:grid-cols-6">
	<div>
		<div class="text-muted-foreground text-xs uppercase">PRUM</div>
		<div class="text-lg font-semibold">{money(position.prum)}</div>
	</div>
	<div>
		<div class="text-muted-foreground text-xs uppercase">Quantity</div>
		<div class="text-lg font-semibold">{quantity(position.quantity)}</div>
	</div>
	<div>
		<div class="text-muted-foreground text-xs uppercase">Invested</div>
		<div class="text-lg font-semibold">{money(position.invested)}</div>
	</div>
	<div>
		<div class="text-muted-foreground text-xs uppercase">Price</div>
		<div class="text-lg font-semibold">{money(position.price)}</div>
	</div>
	<div>
		<div class="text-muted-foreground text-xs uppercase">Market value</div>
		<div class="text-lg font-semibold">{money(position.market_value)}</div>
	</div>
	<div>
		<div class="text-muted-foreground text-xs uppercase">Gain / loss</div>
		<div class="text-lg font-semibold {tone}">
			{money(position.gain)}
			<span class="text-sm">({percent(position.gain_percent)})</span>
		</div>
	</div>
</div>
