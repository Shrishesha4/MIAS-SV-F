<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { geofencingApi } from '$lib/api/geofencing';
	import { getCurrentPosition } from '$lib/utils/geolocation';
	import { MapPin, CheckCircle, XCircle, Loader2, AlertTriangle } from 'lucide-svelte';

	const patientId = page.url.searchParams.get('patient_id');

	type Step = 'idle' | 'loading' | 'success' | 'error' | 'outside';

	let step = $state<Step>('idle');
	let proofCode = $state('');
	let errorMsg = $state('');

	async function verifyLocation() {
		step = 'loading';
		try {
			const coords = await getCurrentPosition();
			const result = await geofencingApi.submitPatientProof({
				lat: coords.lat,
				lng: coords.lng,
				accuracy: coords.accuracy,
				patient_id: patientId ?? undefined,
			});

			// Show the server-generated 8-char short code
			proofCode = result.short_code;

			if (result.is_valid) {
				step = 'success';
			} else {
				step = 'outside';
			}
		} catch (err: any) {
			errorMsg = err?.message ?? 'Failed to verify location.';
			step = 'error';
		}
	}
</script>

<svelte:head>
	<title>Verify Location — MIAS</title>
	<meta name="viewport" content="width=device-width, initial-scale=1" />
</svelte:head>

<div class="min-h-screen flex items-center justify-center p-4"
	style="background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);">
	<div class="w-full max-w-sm rounded-2xl overflow-hidden"
		style="background: linear-gradient(to bottom, #1e293b, #0f172a); border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 25px 50px rgba(0,0,0,0.5);">

		<!-- Header -->
		<div class="px-6 pt-6 pb-4 text-center"
			style="background: linear-gradient(to bottom, rgba(59,130,246,0.15), transparent); border-bottom: 1px solid rgba(255,255,255,0.07);">
			<div class="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-3"
				style="background: linear-gradient(135deg, #3b82f6, #2563eb); box-shadow: 0 4px 15px rgba(59,130,246,0.4);">
				<MapPin size={28} color="white" />
			</div>
			<h1 class="text-white font-bold text-xl">Location Verification</h1>
			<p class="text-slate-400 text-sm mt-1">MIAS — Saveetha Medical College</p>
		</div>

		<div class="p-6">
			{#if step === 'idle'}
				<p class="text-slate-300 text-center text-sm mb-6 leading-relaxed">
					Tap the button below to verify you are within campus.
					Your receptionist needs this code to check you in.
				</p>
				<button
					onclick={verifyLocation}
					class="w-full py-4 rounded-xl font-semibold text-white text-base"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 4px 12px rgba(59,130,246,0.35);">
					Verify My Location
				</button>

			{:else if step === 'loading'}
				<div class="flex flex-col items-center gap-4 py-6">
					<div class="animate-spin"><Loader2 size={40} color="#60a5fa" /></div>
					<p class="text-slate-300 text-sm">Detecting your location…</p>
				</div>

			{:else if step === 'success'}
				<div class="flex flex-col items-center gap-4">
					<CheckCircle size={48} color="#22c55e" />
					<p class="text-green-400 font-semibold text-lg">Location Verified ✓</p>
					<p class="text-slate-400 text-sm text-center">Show this code to the receptionist:</p>
					<div class="w-full rounded-xl text-center py-5"
						style="background: rgba(34,197,94,0.12); border: 2px solid rgba(34,197,94,0.4);">
						<span class="text-4xl font-mono font-bold text-green-300 tracking-[0.25em]">{proofCode}</span>
					</div>
					<p class="text-slate-500 text-xs text-center">Valid for 15 minutes. Do not refresh this page.</p>
				</div>

			{:else if step === 'outside'}
				<div class="flex flex-col items-center gap-4">
					<AlertTriangle size={48} color="#f59e0b" />
					<p class="text-amber-400 font-semibold text-lg">Outside Campus Zone</p>
					<p class="text-slate-400 text-sm text-center leading-relaxed">
						Your location is outside the designated campus area.
						Please move to the campus before checking in.
					</p>
					<button
						onclick={() => { step = 'idle'; }}
						class="w-full py-3 rounded-xl font-semibold text-white"
						style="background: linear-gradient(to bottom, #f59e0b, #d97706);">
						Try Again
					</button>
				</div>

			{:else if step === 'error'}
				<div class="flex flex-col items-center gap-4">
					<XCircle size={48} color="#ef4444" />
					<p class="text-red-400 font-semibold text-lg">Verification Failed</p>
					<p class="text-slate-400 text-sm text-center">{errorMsg}</p>
					<button
						onclick={() => { step = 'idle'; }}
						class="w-full py-3 rounded-xl font-semibold text-white"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
						Try Again
					</button>
				</div>
			{/if}
		</div>
	</div>
</div>
