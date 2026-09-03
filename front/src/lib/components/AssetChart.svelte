<script lang="ts">
	import type { PricePoint, PrumPoint, Transaction } from '$lib/types/api';
	import { currencySymbol } from '$lib/utils';
	import {
		CategoryScale,
		Chart,
		Legend,
		LinearScale,
		LineController,
		LineElement,
		PointElement,
		ScatterController,
		Tooltip
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

	// The PRUM curve comes from the API on purpose: recomputing it here would
	// ignore the opening position and show a PRUM well below the real one.
	let {
		transactions = [],
		priceHistory = [],
		prumHistory = [],
		currency = 'EUR'
	}: {
		transactions?: Transaction[];
		priceHistory?: PricePoint[];
		prumHistory?: PrumPoint[];
		currency?: string;
	} = $props();

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	const symbol = $derived(currencySymbol(currency));

	function isDark() {
		return document.documentElement.classList.contains('dark');
	}

	function fmtISO(iso: string): string {
		const [year, month, day] = iso.split('-');
		const d = new Date(Number(year), Number(month) - 1, Number(day));
		return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
	}

	function buildChart() {
		if (!canvas) return;
		if (chart) chart.destroy();

		const dark = isDark();
		const gridColor = dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
		const textColor = dark ? '#e5e7eb' : '#374151';

		const isoSet = new Set<string>([
			...priceHistory.map((p) => p.date),
			...prumHistory.map((p) => p.date),
			...transactions.map((tx) => tx.date)
		]);
		const allISO = [...isoSet].sort();
		const allDates = allISO.map(fmtISO);
		const labelIndex = new Map(allISO.map((iso, i) => [iso, i]));

		// One scatter point per day, averaging same-day transactions.
		const txByDate = new Map<string, Transaction[]>();
		for (const tx of transactions) {
			if (!txByDate.has(tx.date)) txByDate.set(tx.date, []);
			txByDate.get(tx.date)!.push(tx);
		}

		const scatterPoints: { x: string; y: number }[] = [];
		const pointColors: string[] = [];
		const dailyTransactions: Transaction[][] = [];
		for (const iso of [...txByDate.keys()].sort()) {
			const txs = txByDate.get(iso)!;
			const avgPrice = txs.reduce((sum, tx) => sum + tx.unit_price, 0) / txs.length;
			scatterPoints.push({ x: fmtISO(iso), y: avgPrice });
			dailyTransactions.push(txs);
			pointColors.push(
				txs.some((tx) => tx.side === 'sell') ? 'rgba(239,68,68,0.9)' : 'rgba(34,197,94,0.9)'
			);
		}

		// Step curve: hold each PRUM until the next transaction changes it.
		const prumLine: (number | null)[] = Array(allDates.length).fill(null);
		for (const point of prumHistory) {
			const idx = labelIndex.get(point.date);
			if (idx !== undefined) prumLine[idx] = point.prum;
		}
		let last: number | null = null;
		for (let i = 0; i < prumLine.length; i++) {
			if (prumLine[i] !== null) last = prumLine[i];
			else if (last !== null) prumLine[i] = last;
		}

		const histLine: (number | null)[] = Array(allDates.length).fill(null);
		for (const p of priceHistory) {
			const idx = labelIndex.get(p.date);
			if (idx !== undefined) histLine[idx] = p.price;
		}

		const datasets: object[] = [
			{
				type: 'line',
				label: 'PRUM',
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
									return txs.map(
										(tx) =>
											`${tx.side.toUpperCase()} ${tx.quantity} @ ${symbol}${tx.unit_price.toFixed(4)}`
									);
								}
								const raw = ctx.raw as { y: number } | number;
								const val = typeof raw === 'number' ? raw : raw.y;
								return `${ctx.dataset.label}: ${symbol}${val.toFixed(4)}`;
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
						ticks: { color: textColor, callback: (v) => `${symbol}${v}` },
						grid: { color: gridColor }
					}
				}
			}
		});
	}

	$effect(() => {
		transactions;
		priceHistory;
		prumHistory;
		buildChart();
		return () => {
			chart?.destroy();
			chart = null;
		};
	});
</script>

<div class="relative h-72 w-full">
	<canvas bind:this={canvas}></canvas>
</div>
