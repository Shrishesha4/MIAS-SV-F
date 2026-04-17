<script lang="ts">
	import { Briefcase, Building2, CircleOff, HeartPulse, Landmark, Shield, Wallet } from 'lucide-svelte';
	import type { InsurancePolicy } from '$lib/api/types';
	import { getPrimaryInsuranceVisual } from '$lib/utils/patient-insurance';
	import { getPatientCategoryVisual } from '$lib/utils/patient-category';
	import { resolvePhotoSrc } from '$lib/utils/photo';

	interface Props {
		name: string;
		src?: string | null;
		size?: 'sm' | 'md' | 'lg' | 'xl';
		insurancePolicies?: InsurancePolicy[] | null;
		insuranceLabel?: string | null;
		patientCategory?: string | null;
		patientCategoryColorPrimary?: string | null;
		patientCategoryColorSecondary?: string | null;
	}

	const {
		name,
		src = null,
		size = 'md',
		insurancePolicies = null,
		insuranceLabel = null,
		patientCategory = null,
		patientCategoryColorPrimary = null,
		patientCategoryColorSecondary = null,
	}: Props = $props();

	const sizeConfig = {
		sm: {
			frame: 'h-10 w-10',
			badge: 'h-6 w-6',
			badgeInner: 'h-4.5 w-4.5',
			badgeIcon: 'h-2.5 w-2.5',
			badgeText: 'text-[9px]',
			text: 'text-sm',
			ringSize: 3,
		},
		md: {
			frame: 'h-12 w-12',
			badge: 'h-6 w-6',
			badgeInner: 'h-4.5 w-4.5',
			badgeIcon: 'h-3 w-3',
			badgeText: 'text-[10px]',
			text: 'text-base',
			ringSize: 4,
		},
		lg: {
			frame: 'h-14 w-14',
			badge: 'h-7 w-7',
			badgeInner: 'h-5 w-5',
			badgeIcon: 'h-3.5 w-3.5',
			badgeText: 'text-[11px]',
			text: 'text-lg',
			ringSize: 5,
		},
		xl: {
			frame: 'h-28 w-28',
			badge: 'h-9 w-9',
			badgeInner: 'h-7 w-7',
			badgeIcon: 'h-4 w-4',
			badgeText: 'text-sm',
			text: 'text-3xl',
			ringSize: 8,
		},
	} as const;

	const insuranceIcons = {
		shield: Shield,
		landmark: Landmark,
		briefcase: Briefcase,
		building: Building2,
		wallet: Wallet,
		heart: HeartPulse,
		off: CircleOff,
	} as const;

	const visual = $derived(getPrimaryInsuranceVisual(insurancePolicies, insuranceLabel));
	const patientVisual = $derived(getPatientCategoryVisual(patientCategory, patientCategoryColorPrimary, patientCategoryColorSecondary));
	const config = $derived(sizeConfig[size]);
	const InsuranceIcon = $derived(insuranceIcons[visual.iconKey]);
	const resolvedSrc = $derived(resolvePhotoSrc(src));
	const initials = $derived(
		String(name ?? '')
			.split(' ')
			.map((part) => part[0])
			.filter(Boolean)
			.join('')
			.toUpperCase()
			.slice(0, 2) || '?'
	);
	const avatarShadow = $derived(
		`box-shadow: 0 0 0 3px ${patientVisual.strokeColor}, 0 2px 6px rgba(0,0,0,0.15);`
	);
</script>

<div class={`relative shrink-0 ${config.frame}`} title={visual.label}>
	<div
		class={`relative h-full w-full overflow-hidden rounded-full ${config.text}`}
		// style={`background: ${patientVisual.background};`}
		style={`${avatarShadow} background: ${patientVisual.background};`}
	>
		{#if resolvedSrc}
			<img src={resolvedSrc} alt={name} class="h-full w-full rounded-full object-cover" />
	
		{:else}
			<div class="flex h-full w-full items-center justify-center rounded-full font-black tracking-tight text-white">
				{initials}
			</div>
		{/if}
	</div>

	<!-- <div
		class={`absolute -bottom-0.5 -right-0.5 flex items-center justify-center rounded-full ${config.badge}`}
		style={`background: white; border: 2px solid rgba(255,255,255,0.96); box-shadow: 0 10px 18px ${visual.glowColor}, 0 0 0 1px ${visual.badgeBorder};`}
	>
		<div
			class={`flex items-center justify-center rounded-full ${config.badgeInner}`}
			style={`background: ${visual.badgeBackground}; color: ${visual.textColor}; box-shadow: inset 0 1px 0 rgba(255,255,255,0.92), 0 0 0 1px ${visual.badgeBorder};`}
		>
			{#if visual.badgeText}
				<span class={`font-black leading-none tracking-tight ${config.badgeText}`}>{visual.badgeText}</span>
			{:else}
				<InsuranceIcon class={config.badgeIcon} style="filter: drop-shadow(0 1px 0 rgba(255,255,255,0.35));" />
			{/if}
		</div>
	</div> -->
</div>
