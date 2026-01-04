<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Dialog, DialogContent, DialogHeader, DialogTitle } from '$lib/components/ui/dialog';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import StockAutocomplete from '$lib/components/StockAutocomplete.svelte';
	import { useStockSearch, type SearchResult } from '$lib/hooks/useStockSearch.svelte';
	import type { Stock, StockFormData } from '$lib/types/config';

	type Props = {
		open: boolean;
		stock?: Stock | null;
		prefilledSymbol?: string | null;
		prefilledName?: string | null;
		onClose: () => void;
		onSubmit: (stock: Omit<Stock, 'id'>) => void;
	};

	let { open = $bindable(), stock = null, prefilledSymbol = null, prefilledName = null, onClose, onSubmit }: Props = $props();

	let formData: StockFormData = $state({
		symbol: '',
		shares_number: '',
		cost: '',
		current_repartition: '',
		target_repartition: '',
		arbitration_threshold: '',
		threshold_to_alert: ''
	});

	let errors: Partial<Record<keyof StockFormData, string>> = $state({});
	let selectedName = $state<string | null>(null);
	
	// Use the stock search hook
	const stockSearch = useStockSearch();

	// Initialize form when stock or prefilledSymbol changes
	$effect(() => {
		if (stock) {
			formData = {
				symbol: stock.symbol,
				shares_number: stock.shares_number.toString(),
				cost: stock.cost.toString(),
				current_repartition: stock.current_repartition.toString(),
				target_repartition: stock.target_repartition.toString(),
				arbitration_threshold: stock.arbitration_threshold.toString(),
				threshold_to_alert: stock.threshold_to_alert.toString()
			};
			selectedName = stock.name;
		} else if (open) {
			// Only reset when dialog opens, not on every effect run
			formData = {
				symbol: prefilledSymbol || '',
				shares_number: '',
				cost: '',
				current_repartition: '',
				target_repartition: '',
				arbitration_threshold: '5',
				threshold_to_alert: '10'
			};
			selectedName = prefilledName;
			errors = {};
		}
	});

	function handleSymbolInput() {
		// Clear selected name when user types
		if (selectedName && formData.symbol !== stockSearch.state.results.find(r => r.name === selectedName)?.symbol) {
			selectedName = null;
		}
		// Debounced search
		stockSearch.debouncedSearch(formData.symbol);
	}

	function selectStock(result: SearchResult) {
		formData.symbol = result.symbol;
		selectedName = result.name;
		stockSearch.clearResults();
	}

	function resetForm() {
		formData = {
			symbol: '',
			shares_number: '',
			cost: '',
			current_repartition: '',
			target_repartition: '',
			arbitration_threshold: '5',
			threshold_to_alert: '10'
		};
		errors = {};
		stockSearch.clearResults();
		selectedName = null;
	}

	function validateForm(): boolean {
		errors = {};
		let isValid = true;

		if (!formData.symbol.trim()) {
			errors.symbol = 'Symbol is required';
			isValid = false;
		}

		const numericFields: (keyof StockFormData)[] = [
			'shares_number',
			'cost',
			'current_repartition',
			'target_repartition',
			'arbitration_threshold',
			'threshold_to_alert'
		];

		numericFields.forEach((field) => {
			const value = formData[field];
			console.log('Validating field', field, 'with value', value);
			if (!value) {
				errors[field] = 'This field is required';
				isValid = false;
			} else if (isNaN(Number(value))) {
				errors[field] = 'Must be a valid number';
				isValid = false;
			} else if (Number(value) < 0) {
				errors[field] = 'Must be a positive number';
				isValid = false;
			}
		});

		// Validate percentages
		if (
			formData.current_repartition &&
			!isNaN(Number(formData.current_repartition)) &&
			(Number(formData.current_repartition) < 0 || Number(formData.current_repartition) > 100)
		) {
			errors.current_repartition = 'Must be between 0 and 100';
			isValid = false;
		}

		if (
			formData.target_repartition &&
			!isNaN(Number(formData.target_repartition)) &&
			(Number(formData.target_repartition) < 0 || Number(formData.target_repartition) > 100)
		) {
			errors.target_repartition = 'Must be between 0 and 100';
			isValid = false;
		}

		return isValid;
	}

	function handleSubmit() {
		if (!validateForm()) return;

		const stockData: Omit<Stock, 'id'> = {
			name: selectedName || prefilledName,
			symbol: formData.symbol.trim().toUpperCase(),
			shares_number: Number(formData.shares_number),
			cost: Number(formData.cost),
			current_repartition: Number(formData.current_repartition),
			target_repartition: Number(formData.target_repartition),
			arbitration_threshold: Number(formData.arbitration_threshold),
			threshold_to_alert: Number(formData.threshold_to_alert)
		};

		onSubmit(stockData);
		handleClose();
	}

	function handleClose() {
		resetForm();
		onClose();
	}

</script>

<Dialog bind:open>
	<DialogContent class="w-[95vw] sm:w-[600px] max-h-[85vh] overflow-y-auto">
		<DialogHeader>
			<DialogTitle>{stock ? 'Edit Stock' : 'Add New Stock'}</DialogTitle>
		</DialogHeader>

	<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-3 sm:space-y-4">
		<div class="space-y-2 relative">
			<Label for="symbol">Stock Symbol *</Label>
			<Input
				id="symbol"
				bind:value={formData.symbol}
				oninput={handleSymbolInput}
				onfocus={() => { if (stockSearch.state.results.length > 0) stockSearch.setShowResults(true); }}
				placeholder="e.g., AAPL, GOOGL"
				class={errors.symbol ? 'border-red-500' : ''}
				autocomplete="off"
			/>
			{#if stockSearch.state.loading}
				<div class="absolute right-3 top-8">
					<div class="animate-spin h-4 w-4 border-2 border-slate-300 border-t-blue-600 rounded-full"></div>
				</div>
			{/if}
			{#if selectedName}
				<p class="text-sm text-slate-600">{selectedName}</p>
			{/if}
			{#if errors.symbol}
				<p class="text-sm text-red-500">{errors.symbol}</p>
			{/if}
			
			<StockAutocomplete 
				results={stockSearch.state.results}
				show={stockSearch.state.showResults}
				onSelect={selectStock}
			/>
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
			<div class="space-y-2">
				<Label for="shares_number">Number of Shares *</Label>
				<Input
					id="shares_number"
					type="number"
					step="0.00000001"
					bind:value={formData.shares_number}
					placeholder="10.2"
					class={errors.shares_number ? 'border-red-500' : ''}
				/>
				{#if errors.shares_number}
					<p class="text-sm text-red-500">{errors.shares_number}</p>
				{/if}
			</div>

			<div class="space-y-2">
				<Label for="cost">Cost *</Label>
				<Input
					id="cost"
					type="number"
					step="0.00000001"
					bind:value={formData.cost}
					placeholder="150.25"
					class={errors.cost ? 'border-red-500' : ''}
				/>
				{#if errors.cost}
					<p class="text-sm text-red-500">{errors.cost}</p>
				{/if}
			</div>
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
			<div class="space-y-2">
				<Label for="current_repartition">Current Repartition (%) *</Label>
				<Input
					id="current_repartition"
					type="number"
					step="0.01"
					bind:value={formData.current_repartition}
					placeholder="35"
					class={errors.current_repartition ? 'border-red-500' : ''}
				/>
				{#if errors.current_repartition}
					<p class="text-sm text-red-500">{errors.current_repartition}</p>
				{/if}
			</div>

			<div class="space-y-2">
				<Label for="target_repartition">Target Repartition (%) *</Label>
				<Input
					id="target_repartition"
					type="number"
					step="0.01"
					bind:value={formData.target_repartition}
					placeholder="40"
					class={errors.target_repartition ? 'border-red-500' : ''}
				/>
				{#if errors.target_repartition}
					<p class="text-sm text-red-500">{errors.target_repartition}</p>
				{/if}
			</div>
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
			<div class="space-y-2">
				<Label for="arbitration_threshold">Arbitration Threshold (%) *</Label>
				<Input
					id="arbitration_threshold"
					type="number"
					step="0.1"
					bind:value={formData.arbitration_threshold}
					placeholder="5"
					class={errors.arbitration_threshold ? 'border-red-500' : ''}
				/>
				{#if errors.arbitration_threshold}
					<p class="text-sm text-red-500">{errors.arbitration_threshold}</p>
				{/if}
			</div>

			<div class="space-y-2">
				<Label for="threshold_to_alert">Alert Threshold (%) *</Label>
				<Input
					id="threshold_to_alert"
					type="number"
					step="0.1"
					bind:value={formData.threshold_to_alert}
					placeholder="10"
					class={errors.threshold_to_alert ? 'border-red-500' : ''}
				/>
				{#if errors.threshold_to_alert}
					<p class="text-sm text-red-500">{errors.threshold_to_alert}</p>
				{/if}
			</div>
		</div>

		<div class="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 sm:gap-2 pt-2">
			<Button type="button" variant="outline" onclick={handleClose} class="w-full sm:w-auto">Cancel</Button>
			<Button type="submit" class="w-full sm:w-auto">{stock ? 'Update' : 'Add'} Stock</Button>
		</div>
	</form>
	</DialogContent>
</Dialog>