<script lang="ts">
	import StockSearch from '$lib/components/StockSearch.svelte';
</script>

<div class="container">
	<header>
		<h1>Stock Alerting</h1>
		<p>Search for stocks and manage your portfolio</p>
	</header>

	<main>
		<StockSearch />
	</main>
</div>

<style>
	.container {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
	}

	header {
		text-align: center;
		margin-bottom: 3rem;
	}

	h1 {
		font-size: 2.5rem;
		font-weight: 700;
		color: #1e293b;
		margin-bottom: 0.5rem;
	}

	p {
		font-size: 1.125rem;
		color: #64748b;
	}

	main {
		display: flex;
		justify-content: center;
	}
</style>
