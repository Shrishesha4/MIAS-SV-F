<script lang="ts">
	import { toastStore, type Toast } from '$lib/stores/toast';
	import { CheckCircle, AlertTriangle, Info, XCircle, X } from 'lucide-svelte';

	let toasts = $state<Toast[]>([]);
	toastStore.subscribe(v => toasts = v);

	const iconMap = {
		success: CheckCircle,
		error: XCircle,
		warning: AlertTriangle,
		info: Info
	};

	const colorMap = {
		success: { bg: 'linear-gradient(to bottom, #a7f3d0, #6ee7b7)', border: 'rgba(16,185,129,0.4)', text: '#065f46' },
		error: { bg: 'linear-gradient(to bottom, #fecaca, #fca5a5)', border: 'rgba(239,68,68,0.4)', text: '#991b1b' },
		warning: { bg: 'linear-gradient(to bottom, #fef3c7, #fde68a)', border: 'rgba(245,158,11,0.4)', text: '#92400e' },
		info: { bg: 'linear-gradient(to bottom, #dbeafe, #bfdbfe)', border: 'rgba(59,130,246,0.4)', text: '#1e40af' }
	};
</script>

{#if toasts.length > 0}
	<div class="fixed top-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm">
		{#each toasts as toast (toast.id)}
			{@const Icon = iconMap[toast.type]}
			{@const colors = colorMap[toast.type]}
			<div
				class="flex items-start gap-3 px-4 py-3 rounded-xl shadow-lg animate-slide-in"
				style="background: {colors.bg}; border: 1px solid {colors.border}; box-shadow: 0 4px 12px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.6);"
			>
				<Icon class="w-5 h-5 flex-shrink-0 mt-0.5" style="color: {colors.text}" />
				<p class="text-sm font-medium flex-1" style="color: {colors.text}">{toast.message}</p>
				<button
					class="flex-shrink-0 cursor-pointer opacity-60 hover:opacity-100"
					onclick={() => toastStore.removeToast(toast.id)}
				>
					<X class="w-4 h-4" style="color: {colors.text}" />
				</button>
			</div>
		{/each}
	</div>
{/if}

<style>
	@keyframes slideIn {
		from { transform: translateX(100%); opacity: 0; }
		to { transform: translateX(0); opacity: 1; }
	}
	.animate-slide-in {
		animation: slideIn 0.3s ease-out;
	}
</style>
