<script lang="ts">
	import { Briefcase, Building2, CircleOff, HeartPulse, Landmark, Shield, Wallet } from 'lucide-svelte';
	import type { InsurancePolicy } from '$lib/api/types';
	import { getInsuranceVisuals } from '$lib/utils/patient-insurance';

	interface Props {
		insurancePolicies?: InsurancePolicy[] | null;
		insuranceLabel?: string | null;
		maxVisible?: number;
		compact?: boolean;
		variant?: 'pill' | 'circle';
	}

	const { insurancePolicies = null, insuranceLabel = null, maxVisible = 3, compact = false, variant = 'pill' }: Props = $props();

	const insuranceIcons = {
		shield: Shield,
		landmark: Landmark,
		briefcase: Briefcase,
		building: Building2,
		wallet: Wallet,
		heart: HeartPulse,
		off: CircleOff,
	} as const;

	const visuals = $derived(getInsuranceVisuals(insurancePolicies, insuranceLabel));
	const visibleVisuals = $derived(visuals.slice(0, maxVisible));
	const hiddenCount = $derived(Math.max(visuals.length - visibleVisuals.length, 0));

	function getCircleSymbol(visual: (typeof visuals)[number]): string {
		if (visual.badgeText) return visual.badgeText.slice(0, 2);
		return visual.label
			.split(/\s+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((w) => w[0].toUpperCase())
			.join('');
	}
</script>

{#if variant === 'circle'}
	<div class="flex items-center" style="gap: 3px;">
		{#each visibleVisuals as visual (`${visual.key}-${visual.label}`)}
			<span
				title={visual.label}
				class="inline-flex items-center justify-center rounded-full font-black leading-none tracking-tight"
				style={`
					width: ${compact ? '20px' : '24px'};
					height: ${compact ? '20px' : '24px'};
					font-size: ${compact ? '8px' : '9px'};
					background: ${visual.background};
					color: #fff;
					box-shadow: 0 1px 3px ${visual.glowColor}, inset 0 1px 0 rgba(255,255,255,0.28);
					border: 1.5px solid rgba(255,255,255,0.38);
				`}
			>
				{getCircleSymbol(visual)}
			</span>
		{/each}
		{#if hiddenCount > 0}
			<span
				class="inline-flex items-center justify-center rounded-full font-bold leading-none"
				style={`width: ${compact ? '20px' : '24px'}; height: ${compact ? '20px' : '24px'}; font-size: ${compact ? '8px' : '9px'}; background: rgba(100,116,139,0.15); color: #64748b; border: 1.5px solid rgba(148,163,184,0.4);`}
			>
				+{hiddenCount}
			</span>
		{/if}
	</div>
{:else}
	<div class={`flex flex-wrap gap-1.5 ${compact ? '' : 'mt-2'}`}>
		{#each visibleVisuals as visual (`${visual.key}-${visual.label}`)}
			{@const InsuranceIcon = insuranceIcons[visual.iconKey]}
			<span
				class={`inline-flex items-center rounded-full font-semibold ${compact ? 'gap-1 px-2 py-0.5 text-[10px]' : 'gap-1.5 px-2.5 py-1 text-[11px]'}`}
				style={`background: ${visual.badgeBackground}; color: ${visual.textColor}; border: 1px solid ${visual.badgeBorder}; box-shadow: inset 0 1px 0 rgba(255,255,255,0.72);`}
			>
				{#if visual.badgeText}
					<span class={`font-black leading-none tracking-tight ${compact ? 'text-[9px]' : 'text-[10px]'}`}>{visual.badgeText}</span>
				{:else}
					<InsuranceIcon class={compact ? 'h-2.5 w-2.5' : 'h-3 w-3'} />
				{/if}
				<span>{visual.label}</span>
			</span>
		{/each}

		{#if hiddenCount > 0}
			<span class="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
				+{hiddenCount}
			</span>
		{/if}
	</div>
{/if}
