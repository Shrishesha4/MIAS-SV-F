<script lang="ts">
	import { browser } from '$app/environment';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import { geofencingApi } from '$lib/api/geofencing';
	import { MapPin, CheckCircle, XCircle, Loader2, QrCode, RefreshCw } from 'lucide-svelte';
	import QRCode from 'qrcode';

	interface Props {
		open: boolean;
		patientId: string;
		patientName: string;
		onclose: () => void;
		onverified: (proofId: string) => void;
	}

	let { open, patientId, patientName, onclose, onverified }: Props = $props();

	const verifyUrl = $derived(
		browser
			? `${window.location.origin}/patient-verify?patient_id=${encodeURIComponent(patientId)}`
			: ''
	);

	let qrDataUrl = $state('');
	let proofCodeInput = $state('');
	let verifying = $state(false);
	let verifyError = $state('');
	let verifySuccess = $state(false);

	// Generate QR code whenever the URL changes
	$effect(() => {
		if (!verifyUrl) return;
		QRCode.toDataURL(verifyUrl, { width: 180, margin: 1, color: { dark: '#1e293b', light: '#f1f5f9' } })
			.then((url) => { qrDataUrl = url; })
			.catch(() => {});
	});

	// Reset state when modal opens
	$effect(() => {
		if (open) {
			proofCodeInput = '';
			verifyError = '';
			verifySuccess = false;
			verifying = false;
		}
	});

	async function handleVerify() {
		const raw = proofCodeInput.trim();
		if (!raw) {
			verifyError = 'Enter the code shown on the patient\'s phone.';
			return;
		}
		verifying = true;
		verifyError = '';
		try {
			// Find the matching proof by polling with the short code.
			// The patient page shows the first 8 hex chars of the UUID (no dashes).
			// We call the status endpoint with the raw input treated as UUID prefix search.
			// For simplicity, patients can also share full proof_id; we accept both.
			const status = await geofencingApi.getProofStatus(raw);
			if (status.is_expired) {
				verifyError = 'This code has expired. Ask the patient to generate a new one.';
				return;
			}
			if (status.is_consumed) {
				verifyError = 'This code was already used.';
				return;
			}
			if (!status.is_valid) {
				verifyError = 'Patient is outside campus premises. Check-in blocked.';
				return;
			}
			verifySuccess = true;
			onverified(raw);
		} catch (err: any) {
			verifyError = err?.response?.data?.detail ?? 'Invalid or unknown code.';
		} finally {
			verifying = false;
		}
	}

	function reset() {
		proofCodeInput = '';
		verifyError = '';
		verifySuccess = false;
		verifying = false;
	}
</script>

<AquaModal {open} title="Patient Location Verification" {onclose}>
	<div class="flex flex-col gap-5 p-1">
		<!-- Instruction -->
		<div class="rounded-xl p-3 text-sm"
			style="background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.25);">
			<p class="text-blue-300 font-medium mb-1">Ask the patient to:</p>
			<ol class="text-slate-400 space-y-1 pl-4 list-decimal">
				<li>Scan the QR code with their phone <em>or</em> open the link below</li>
				<li>Tap "Verify My Location" on their phone</li>
				<li>Share the 8-character code shown</li>
			</ol>
		</div>

		<!-- QR + URL -->
		<div class="flex flex-col items-center gap-3">
			{#if qrDataUrl}
				<img src={qrDataUrl} alt="Patient verify QR code" class="rounded-xl"
					style="border: 2px solid rgba(255,255,255,0.1);" width="160" height="160" />
			{:else}
				<div class="w-40 h-40 rounded-xl flex items-center justify-center"
					style="background: rgba(255,255,255,0.05);">
					<Loader2 size={28} class="animate-spin text-slate-400" />
				</div>
			{/if}
			<p class="text-xs text-slate-500 break-all text-center max-w-xs">{verifyUrl}</p>
		</div>

		<!-- Code input -->
		{#if verifySuccess}
			<div class="rounded-xl p-4 flex items-center gap-3"
				style="background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.3);">
				<CheckCircle size={22} color="#22c55e" />
				<p class="text-green-400 font-semibold text-sm">Location verified — proceeding with check-in</p>
			</div>
		{:else}
			<div class="flex flex-col gap-2">
				<label for="proof-code-input" class="text-slate-300 text-sm font-medium">
					Enter code shown on patient's phone
				</label>
				<input
					id="proof-code-input"
					type="text"
					bind:value={proofCodeInput}
					placeholder="e.g. A1B2C3D4 or full UUID"
					maxlength="36"
					class="w-full px-4 py-3 rounded-xl text-white font-mono text-sm"
					style="background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.15); outline: none;"
					onkeydown={(e) => { if (e.key === 'Enter') handleVerify(); }}
				/>
				{#if verifyError}
					<p class="text-red-400 text-xs flex items-center gap-1">
						<XCircle size={13} />{verifyError}
					</p>
				{/if}
			</div>

			<div class="flex gap-3">
				<button onclick={onclose}
					class="flex-1 py-3 rounded-xl text-sm font-medium text-slate-400"
					style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);">
					Cancel
				</button>
				<button onclick={handleVerify}
					disabled={verifying}
					class="flex-1 py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(59,130,246,0.3); opacity: {verifying ? 0.7 : 1};">
					{#if verifying}<Loader2 size={16} class="animate-spin" />{/if}
					Verify & Check In
				</button>
			</div>
		{/if}
	</div>
</AquaModal>
