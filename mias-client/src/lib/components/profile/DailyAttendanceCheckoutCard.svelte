<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { attendanceApi, type AttendanceStatus } from '$lib/api/attendance';

	let status = $state<AttendanceStatus | null>(null);
	let loading = $state(false);
	let checkingOut = $state(false);
	const roleHiddenForProfileCheckout = new Set([
		'PATIENT',
		'STUDENT',
		'FACULTY',
		'NUTRITIONIST'
	]);

	const showCard = $derived(
		Boolean(
			status &&
			status.checked_in &&
			!status.skip_modal &&
			!roleHiddenForProfileCheckout.has(status.role)
		)
	);

	async function loadStatus() {
		loading = true;
		try {
			status = await attendanceApi.getTodayStatus();
		} catch {
			status = null;
		} finally {
			loading = false;
		}
	}

	async function handleCheckOut() {
		if (checkingOut) return;
		checkingOut = true;
		try {
			status = await attendanceApi.checkOutToday(page.url.pathname);
		} finally {
			checkingOut = false;
		}
	}

	onMount(() => {
		void loadStatus();
	});
</script>

{#if !loading && showCard}
	<div
		class="rounded-2xl border px-3 py-2 text-xs sm:text-sm"
		style="background: rgba(255,255,255,0.95); border-color: rgba(15,23,42,0.12); box-shadow: 0 8px 18px rgba(15,23,42,0.1);"
	>
		<div class="flex items-center justify-between gap-2">
			<p class="font-semibold text-slate-700">
				Checked in{status?.checked_in_at ? ` at ${new Date(status.checked_in_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}
			</p>
			<button
				class="rounded-lg px-2 py-1 text-white disabled:opacity-60"
				style="background: linear-gradient(to bottom, #ef4444, #dc2626);"
				onclick={handleCheckOut}
				disabled={checkingOut}
			>
				{#if checkingOut}
					Checking out...
				{:else}
					Check out
				{/if}
			</button>
		</div>
	</div>
{/if}
