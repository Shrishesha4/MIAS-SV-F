<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { browser } from '$app/environment';
	import { authStore } from '$lib/stores/auth';
	import { authApi } from '$lib/api/auth';
	import GlobalSearchableSelectEnhancer from '$lib/components/ui/GlobalSearchableSelectEnhancer.svelte';
	import './layout.css';

	let { children } = $props();

	onMount(async () => {
		if (!browser) return;
		const auth = get(authStore);
		// If not authenticated, try to restore session from httpOnly cookie
		if (!auth.isAuthenticated && auth.userId) {
			try {
				const result = await authApi.refresh();
				authStore.setTokens(result.access_token, result.user_id, result.role);
			} catch {
				// Refresh failed, will be caught by (app) layout on next navigation
			}
		}
	});
</script>

<svelte:head>
	<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
	<title>MIAS - Medical Information Application System</title>
</svelte:head>

<div class="app-background min-h-screen">
	<GlobalSearchableSelectEnhancer />
	{@render children()}
</div>
