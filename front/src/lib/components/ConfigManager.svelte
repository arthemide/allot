<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardTitle } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
    import * as Table from "$lib/components/ui/table/index.js";
	import StockForm from '$lib/components/StockForm.svelte';
	import type { FundConfig, Stock } from '$lib/types/config';
	import { configApi } from '$lib/services/api-calls';
	import { currencySymbol, formatMoney } from '$lib/utils';
	import Trash2 from "@lucide/svelte/icons/trash-2";
    import Pencil from "@lucide/svelte/icons/pencil";
    import Download from "@lucide/svelte/icons/download";

    // State variables
	let configs: FundConfig[] = $state([]);
	let selectedConfig: FundConfig | null = $state(null);
	let loading: boolean = $state(true);
	let saving: boolean = $state(false);
	let expandedStockId: string | null = $state(null);
	let error: string = $state('');

	// Form states
	let fundName: string = $state('');
	let newFundName: string = $state('');
	let showStockDialog: boolean = $state(false);
	let editingStock: Stock | null = $state(null);
	let prefilledSymbol: string | null = $state(null);
	let prefilledName: string | null = $state(null);

	// Load configurations on mount
	$effect(() => {
		loadConfigs();
	});

	async function loadConfigs() {
		loading = true;
		error = '';
		try {
			configs = await configApi.getAllConfigs();
			if (configs.length > 0 && !selectedConfig) {
				selectConfig(configs[0]);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load configurations';
		} finally {
			loading = false;
		}
	}

	function selectConfig(config: FundConfig) {
		selectedConfig = config;
		fundName = config.fund_name;
	}

	async function createNewConfig() {
		if (!newFundName.trim()) {
			error = 'Fund name is required';
			return;
		}

		saving = true;
		error = '';
		try {
			const newConfig = await configApi.createConfig(newFundName);
			configs = [...configs, newConfig];
			selectConfig(newConfig);
			newFundName = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create configuration';
		} finally {
			saving = false;
		}
	}

	async function updateFundName() {
		if (!selectedConfig || !fundName.trim()) return;

		saving = true;
		error = '';
		try {
			const updated = await configApi.updateConfig(selectedConfig.id!, {
				fund_name: fundName
			});
			if (updated) {
				const index = configs.findIndex((c) => c.id === selectedConfig!.id);
				if (index !== -1) {
					configs[index] = updated;
					configs = [...configs];
					selectedConfig = updated;
				}
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update fund name';
		} finally {
			saving = false;
		}
	}

	async function deleteConfig(id: string) {
		if (!confirm('Are you sure you want to delete this fund configuration?')) return;

		saving = true;
		error = '';
		try {
			await configApi.deleteConfig(id);
			configs = configs.filter((c) => c.id !== id);
			if (selectedConfig?.id === id) {
				selectedConfig = configs.length > 0 ? configs[0] : null;
				fundName = selectedConfig?.fund_name || '';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete configuration';
		} finally {
			saving = false;
		}
	}

	function openAddStockDialog(symbol?: string, name?: string) {
		editingStock = null;
		prefilledSymbol = symbol || null;
		prefilledName = name || null;
		showStockDialog = true;
	}

	export function openAddStockDialogWithSymbol(symbol: string, name: string) {
		openAddStockDialog(symbol, name);
	}

	function openEditStockDialog(stock: Stock) {
		editingStock = stock;
		showStockDialog = true;
	}

	async function handleStockSubmit(stockData: Omit<Stock, 'id'>) {
		console.log('handleStockSubmit', stockData);
		if (!selectedConfig) return;

		saving = true;
		error = '';
		try {
			let updated: FundConfig | null;

			if (editingStock) {
				updated = await configApi.updateStock(selectedConfig.id!, editingStock.id!, stockData);
			} else {
				updated = await configApi.addStock(selectedConfig.id!, stockData);
			}

			if (updated) {
				const index = configs.findIndex((c) => c.id === selectedConfig!.id);
				if (index !== -1) {
					configs[index] = updated;
					configs = [...configs];
					selectedConfig = updated;
				}
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save stock';
		} finally {
			saving = false;
		}
	}

	async function deleteStock(stockId: string) {
		if (!selectedConfig) return;
		if (!confirm('Are you sure you want to delete this stock?')) return;

		saving = true;
		error = '';
		try {
			const updated = await configApi.removeStock(selectedConfig.id!, stockId);
			if (updated) {
				const index = configs.findIndex((c) => c.id === selectedConfig!.id);
				if (index !== -1) {
					configs[index] = updated;
					configs = [...configs];
					selectedConfig = updated;
				}
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete stock';
		} finally {
			saving = false;
		}
	}

	function exportConfig() {
		if (!selectedConfig) return;

		const dataStr = JSON.stringify(
			{
				fund_name: selectedConfig.fund_name,
				stocks: selectedConfig.stocks.map(({ id, ...stock }) => stock)
			},
			null,
			2
		);
		const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
		const exportFileDefaultName = `${selectedConfig.fund_name.replace(/\s+/g, '_')}_config.json`;

		const linkElement = document.createElement('a');
		linkElement.setAttribute('href', dataUri);
		linkElement.setAttribute('download', exportFileDefaultName);
		linkElement.click();
	}
</script>

<div class="container mx-auto p-6 max-w-7xl">

	{#if error}
		<div class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
			{error}
		</div>
	{/if}

	<div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
		<!-- Sidebar: Fund List -->
		<div class="lg:col-span-1">
			<Card>
				<CardTitle>
					<div class="p-6 pb-4">
						<h2 class="text-xl font-semibold">Funds</h2>
					</div>
				</CardTitle>
				<CardContent>
					<div class="space-y-2">
						{#if loading}
							<p class="text-sm text-slate-500">Loading...</p>
						{:else if configs.length === 0}
							<p class="text-sm text-slate-500">No funds yet</p>
						{:else}
							{#each configs as config}
								<button
									class="cursor-pointer w-full text-left px-3 py-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors {selectedConfig?.id ===
									config.id
										? 'bg-slate-100 dark:bg-slate-800 font-medium'
										: ''}"
									onclick={() => selectConfig(config)}
								>
									<div class="flex items-center justify-between">
										<span class="truncate">{config.fund_name}</span>
										<span class="text-xs text-slate-500">{config.stocks.length}</span>
									</div>
								</button>
							{/each}
						{/if}
					</div>

					<div class="mt-4 pt-4 border-t">
						<div class="space-y-2">
							<Label for="new-fund-name">New Fund</Label>
							<Input
								id="new-fund-name"
								bind:value={newFundName}
								placeholder="Fund name"
								disabled={saving}
							/>
							<Button
								class="w-full"
								onclick={createNewConfig}
								disabled={saving || !newFundName.trim()}
							>
								{saving ? 'Creating...' : 'Create Fund'}
							</Button>
						</div>
					</div>
				</CardContent>
			</Card>
		</div>

		<!-- Main Content: Stock Management -->
		<div class="lg:col-span-3">
			{#if selectedConfig}
				<Card>
					<CardTitle>
						<div class="p-6 pb-4 flex items-center justify-between">
							<div class="flex-1">
								<Input
									bind:value={fundName}
									class="text-2xl font-semibold border-0 px-0 focus-visible:ring-0"
									placeholder="Fund name"
									onblur={updateFundName}
						/>
					</div>
					<div class="flex gap-2">
						<Button variant="outline" onclick={exportConfig} disabled={saving}>
							<Download />
						</Button>
						<Button
							variant="destructive"
							onclick={() => deleteConfig(selectedConfig!.id!)}
							disabled={saving}
						>
							<Trash2 />
						</Button>
					</div>
				</div>
			</CardTitle>
			<CardContent>
				<div class="space-y-4">
					<div class="flex justify-between items-center">
						<h3 class="text-lg font-semibold">Stocks ({selectedConfig.stocks.length})</h3>
						<Button onclick={() => openAddStockDialog()} disabled={saving}>
							Add Stock
						</Button>
					</div>					{#if selectedConfig.stocks.length === 0}
								<div class="text-center py-12 text-slate-500">
									<p class="text-lg font-medium mb-2">No stocks in this fund</p>
									<p class="text-sm">Click "Add Stock" to get started</p>
								</div>
							{:else}
								<div class="rounded-md border">
									<Table.Root>
                                        <Table.Header>
                                            <Table.Row>
												<Table.Head class="w-[100px]">Name/Symbol</Table.Head>
                                                <Table.Head>Shares</Table.Head>
                                                <Table.Head>Cost</Table.Head>
                                                <Table.Head>Today Price</Table.Head>
												<Table.Head>Market Value</Table.Head>
												<Table.Head>Gain/Loss</Table.Head>
												<Table.Head class="text-right">Actions</Table.Head>
                                            </Table.Row>
                                        </Table.Header>
										<Table.Body>
											{#each selectedConfig.stocks as stock}
												<Table.Row class="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" onclick={() => expandedStockId = expandedStockId === stock.id ? null : stock.id}>
													<Table.Cell class="font-medium">
														<div class="flex flex-col">
															<span>{stock.name}</span>
															<span class="text-sm text-slate-500">{stock.symbol}</span>
														</div>
													</Table.Cell>
													<Table.Cell>{stock.shares_number}</Table.Cell>
													<Table.Cell>{formatMoney(stock.cost, stock.currency)}</Table.Cell>
													<Table.Cell>{formatMoney(stock.today_price, stock.currency)}</Table.Cell>
													<Table.Cell>{formatMoney(stock.market_value, stock.currency)}</Table.Cell>
													<Table.Cell class={stock.gain_loss && stock.gain_loss >= 0 ? 'text-green-600' : 'text-red-600'}>
														{formatMoney(stock.gain_loss, stock.currency)}
													</Table.Cell>
													<Table.Cell class="text-right">
														<div class="flex justify-end gap-2">
															<Button
																size="sm"
																variant="outline"
																onclick={(e) => { e.stopPropagation(); openEditStockDialog(stock); }}
																disabled={saving}
															>
																<Pencil />
															</Button>
															<Button
																size="sm"
																variant="destructive"
																onclick={(e) => { e.stopPropagation(); deleteStock(stock.id!); }}
																disabled={saving}
															>
																<Trash2 />
															</Button>
														</div>
													</Table.Cell>
												</Table.Row>
												{#if expandedStockId === stock.id}
												<Table.Row class="bg-slate-50 dark:bg-slate-800">
													<Table.Cell colspan="7" class="p-4">
														<div class="grid grid-cols-3 gap-4 text-sm">
															<div>
																<span class="font-semibold">PRUM:</span>
																<span class="ml-2">{formatMoney(stock.prum, stock.currency)}</span>
															</div>
															<div>
																<span class="font-semibold">Gain/Loss %:</span>
																<span class="ml-2 {stock.gain_loss_percentage && stock.gain_loss_percentage >= 0 ? 'text-green-600' : 'text-red-600'}">
																	{stock.gain_loss_percentage ? stock.gain_loss_percentage.toFixed(2) + '%' : 'N/A'}
																</span>
															</div>
															<div>
																<span class="font-semibold">Current Repartition:</span>
																<span class="ml-2">{stock.current_repartition}%</span>
															</div>
															<div>
																<span class="font-semibold">Target Repartition:</span>
																<span class="ml-2">{stock.target_repartition ? stock.target_repartition + '%' : 'N/A'}</span>
															</div>
															<div>
																<span class="font-semibold">Arbitration Threshold:</span>
																<span class="ml-2">{stock.arbitration_threshold}%</span>
															</div>
															<div>
																<span class="font-semibold">Alert Threshold:</span>
																<span class="ml-2">{stock.threshold_to_alert}%</span>
															</div>
														</div>
													</Table.Cell>
												</Table.Row>
												{/if}
											{/each}
										</Table.Body>
									</Table.Root>
								</div>

								<!-- Summary Section -->
								<div class="mt-6 p-4 bg-slate-50 rounded-lg dark:bg-slate-800">
									<h4 class="font-semibold mb-2">Portfolio Summary</h4>
									<div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
										<div>
											<p class="text-slate-600">Total Cost</p>
											<p class="text-lg font-semibold">
												{selectedConfig.total_cost?.toFixed(2) || '0.00'}{currencySymbol(selectedConfig.stocks[0]?.currency)}
											</p>
										</div>
										<div>
											<p class="text-slate-600">Total Market Value</p>
											<p class="text-lg font-semibold">
												{selectedConfig.total_market_value?.toFixed(2) || '0.00'}{currencySymbol(selectedConfig.stocks[0]?.currency)}
											</p>
										</div>
										<div>
											<p class="text-slate-600">Total Gain/Loss</p>
											<p class="text-lg font-semibold" 
												class:text-green-600={(selectedConfig.total_gain_loss || 0) >= 0} 
												class:text-red-600={(selectedConfig.total_gain_loss || 0) < 0}>
												{selectedConfig.total_gain_loss?.toFixed(2) || '0.00'}{currencySymbol(selectedConfig.stocks[0]?.currency)}
											</p>
										</div>
										<div>
											<p class="text-slate-600">Average Gain/Loss %</p>
											<p class="text-lg font-semibold" 
												class:text-green-600={(selectedConfig.average_gain_loss_percentage || 0) >= 0} 
												class:text-red-600={(selectedConfig.average_gain_loss_percentage || 0) < 0}>
												{selectedConfig.average_gain_loss_percentage?.toFixed(2) || '0.00'}%
											</p>
										</div>
									</div>
								</div>
							{/if}
						</div>
					</CardContent>
				</Card>

				<!-- Stock Form Dialog -->
				<StockForm
					bind:open={showStockDialog}
					stock={editingStock}
					prefilledSymbol={prefilledSymbol}
					prefilledName={prefilledName}
					onClose={() => {
						showStockDialog = false;
						editingStock = null;
						prefilledSymbol = null;
						prefilledName = null;
					}}
					onSubmit={handleStockSubmit}
				/>
			{:else if !loading}
				<Card>
					<CardContent>
						<div class="text-center py-12 text-slate-500">
							<p class="text-lg font-medium mb-2">No fund selected</p>
							<p class="text-sm">Create a new fund to get started</p>
						</div>
					</CardContent>
				</Card>
			{/if}
		</div>
	</div>
</div>
