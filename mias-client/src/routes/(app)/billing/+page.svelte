<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';

	let redirecting = $state(true);

	onMount(() => {
		if (!redirectIfUnauthorized(['BILLING', 'ACCOUNTS'])) {
			redirecting = false;
			return;
		}

		const { role } = get(authStore);
		const targetPath = role === 'ACCOUNTS' ? '/billing/accounts' : '/billing/cashier';

		void goto(targetPath, { replaceState: true });
	});
</script>

<svelte:head>
	<title>Billing & Accounts Portal | MIAS</title>
</svelte:head>

<div class="flex min-h-[60vh] items-center justify-center px-4 py-10">
	<div
		class="flex w-full max-w-sm flex-col items-center gap-4 rounded-[28px] px-6 py-7 text-center"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(245,248,253,0.96)); border: 1px solid rgba(148,163,184,0.24); box-shadow: 0 18px 40px rgba(15,23,42,0.08);"
	>
		<div
			class="h-11 w-11 animate-spin rounded-full border-[3px] border-blue-200 border-t-blue-600"
			aria-hidden="true"
		></div>

		<div class="space-y-1">
			<h1 class="text-base font-black tracking-[0.16em] text-slate-700 uppercase">
				Billing & Accounts Portal
			</h1>
			<p class="text-sm text-slate-500">
				{redirecting ? 'Opening dashboard...' : 'Checking access...'}
			</p>
		</div>
	</div>
</div>
