<script lang="ts">
	import type { AssetTransaction } from '$lib/types/config';
	import {
		Chart,
		ScatterController,
		LineController,
		LineElement,
		PointElement,
		CategoryScale,
		LinearScale,
		Tooltip,
		Legend
	} from 'chart.js';

	Chart.register(
		ScatterController,
		LineController,
		LineElement,
		PointElement,
		CategoryScale,
		LinearScale,
		Tooltip,
		Legend
	);

	let {
		transactions,
		priceHistory = []
	}: {
		transactions: AssetTransaction[];
		priceHistory?: { date: string; price: number }[];
	} = $props();

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	function isDark() {
		return document.documentElement.classList.contains('dark');
	}

	// ISO date key for dedup/sort, formatted label for display
	function toISO(ts: string | number): string {
		return new Date(ts).toISOString().slice(0, 10);
	}

	function fmtISO(iso: string): string {
		const [year, month, day] = iso.split('-');
		const d = new Date(Number(year), Number(month) - 1, Number(day));
		return d.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric', year: '2-digit' });
	}

	function buildChart() {
		if (!canvas) return;
		if (chart) chart.destroy();

		const dark = isDark();
		const gridColor = dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
		const textColor = dark ? '#e5e7eb' : '#374151';

		const sorted = [...transactions].sort(
			(a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
		);

		// Merge all ISO dates from both sources, sort, deduplicate
		const isoSet = new Set<string>([
			...priceHistory.map((p) => toISO(p.date)),
			...sorted.map((tx) => toISO(tx.timestamp))
		]);
		const allISO = [...isoSet].sort();
		const allDates = allISO.map(fmtISO);

		// Map ISO date → index
		const labelIndex = new Map(allISO.map((iso, i) => [iso, i]));

		// Group transactions by date (one point per day)
		const txByDate = new Map<string, AssetTransaction[]>();
		for (const tx of sorted) {
			const iso = toISO(tx.timestamp);
			if (!txByDate.has(iso)) txByDate.set(iso, []);
			txByDate.get(iso)!.push(tx);
		}

		// Scatter: one point per date with average price
		const scatterPoints: { x: string; y: number }[] = [];
		const pointColors: string[] = [];
		const dailyTransactions: AssetTransaction[][] = [];

		const sortedDates = [...txByDate.keys()].sort();
		for (const iso of sortedDates) {
			const txs = txByDate.get(iso)!;
			const avgPrice = txs.reduce((sum, tx) => sum + tx.price, 0) / txs.length;
			const label = fmtISO(iso);
			scatterPoints.push({ x: label, y: avgPrice });
			dailyTransactions.push(txs);

			// Color: prioritize sell > buy, or mixed if multiple types
			const types = new Set(txs.map((tx) => tx.transaction_type));
			if (types.has('sell')) pointColors.push('rgba(239,68,68,0.9)');
			else pointColors.push('rgba(34,197,94,0.9)');
			}

		// PRUM: running average cost basis
		let cumCost = 0;
		let cumQty = 0;
		let lastPrum: number | null = null;
		const prumLine: (number | null)[] = Array(allDates.length).fill(null);
		for (const tx of sorted) {
			if (tx.transaction_type === 'buy') {
				cumCost += tx.total_cost;
				cumQty += tx.quantity;
				lastPrum = cumCost / cumQty;
			}
			if (lastPrum !== null) {
				const idx = labelIndex.get(toISO(tx.timestamp));
				if (idx !== undefined) prumLine[idx] = lastPrum;
			}
		}
		// Forward-fill PRUM gaps
		let last: number | null = null;
		for (let i = 0; i < prumLine.length; i++) {
			if (prumLine[i] !== null) last = prumLine[i];
			else if (last !== null) prumLine[i] = last;
		}

		// History line
		const histLine: (number | null)[] = Array(allDates.length).fill(null);
		for (const p of priceHistory) {
			const idx = labelIndex.get(toISO(p.date));
			if (idx !== undefined) histLine[idx] = p.price;
		}

		const datasets: object[] = [
			{
				type: 'line',
				label: 'AVCO',
				data: prumLine,
				borderColor: 'rgba(251,146,60,1)',
				backgroundColor: 'transparent',
				borderWidth: 2,
				borderDash: [6, 3],
				pointRadius: 0,
				tension: 0,
				spanGaps: true,
				order: 2
			},
			{
				type: 'scatter',
				label: 'Transaction price',
				data: scatterPoints,
				backgroundColor: pointColors,
				pointRadius: 6,
				pointHoverRadius: 8,
				order: 1
			}
		];

		if (priceHistory.length > 0) {
			datasets.push({
				type: 'line',
				label: 'Historical price',
				data: histLine,
				borderColor: 'rgba(99,102,241,0.4)',
				backgroundColor: 'transparent',
				borderWidth: 1,
				pointRadius: 0,
				tension: 0.2,
				spanGaps: true,
				order: 3
			});
		}

		chart = new Chart(canvas, {
			type: 'scatter',
			data: { labels: allDates, datasets } as never,
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { labels: { color: textColor } },
					tooltip: {
						callbacks: {
							title: (items) => {
								// Display the actual X value (date) from the scatter point
								if (items.length > 0 && items[0].dataset.label === 'Transaction price') {
									const point = scatterPoints[items[0].dataIndex];
									return point ? point.x : items[0].label;
								}
								return items[0].label;
							},
							label: (ctx) => {
								if (ctx.dataset.label === 'Transaction price') {
									const txs = dailyTransactions[ctx.dataIndex];
									if (!txs) return '';
									if (txs.length === 1) {
										const tx = txs[0];
										return `${tx.transaction_type.toUpperCase()} ${tx.asset_symbol} — $${tx.price.toFixed(4)}`;
									}
									// Multiple transactions on same day: show all
									return txs.map(
										(tx) => `${tx.transaction_type.toUpperCase()} ${tx.asset_symbol} — $${tx.price.toFixed(4)}`
									);
								}
								const y = (ctx.raw as { y: number } | number);
								const val = typeof y === 'number' ? y : (y as { y: number }).y;
								return `${ctx.dataset.label}: $${val.toFixed(4)}`;
							}
						}
					}
				},
				scales: {
					x: {
						type: 'category',
						ticks: { color: textColor, maxTicksLimit: 8 },
						grid: { color: gridColor }
					},
					y: {
						ticks: { color: textColor, callback: (v) => `$${v}` },
						grid: { color: gridColor }
					}
				}
			}
		});
	}

	$effect(() => {
		transactions;
		priceHistory;
		buildChart();
		return () => {
			chart?.destroy();
			chart = null;
		};
	});
</script>

<div class="relative h-64 w-full">
	<canvas bind:this={canvas}></canvas>
</div>
