<script lang="ts">
	import './layout.css';

	let { children } = $props();
</script>

<svelte:head>
	<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
	<title>MIAS - Medical Information Application System</title>
</svelte:head>

<div class="app-background min-h-screen">
	{@render children()}
</div>
