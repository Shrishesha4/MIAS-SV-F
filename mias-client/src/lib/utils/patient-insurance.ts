import type { InsurancePolicy } from '$lib/api/types';

export type InsuranceIconKey = 'shield' | 'landmark' | 'briefcase' | 'building' | 'wallet' | 'heart' | 'off';

export type InsuranceVisual = {
	key: string;
	label: string;
	iconKey: InsuranceIconKey;
	badgeText?: string | null;
	background: string;
	badgeBackground: string;
	badgeBorder: string;
	textColor: string;
	borderColor: string;
	glowColor: string;
	haloColor: string;
};

type InsuranceBucket = Omit<InsuranceVisual, 'label'>;

const INSURANCE_BUCKETS: Record<string, InsuranceBucket> = {
	government: {
		key: 'government',
		iconKey: 'landmark',
		background: 'linear-gradient(135deg, #34d399, #0f766e)',
		badgeBackground: 'linear-gradient(135deg, rgba(236,253,245,0.98), rgba(209,250,229,0.98))',
		badgeBorder: 'rgba(16,185,129,0.34)',
		textColor: '#047857',
		borderColor: 'rgba(16,185,129,0.4)',
		glowColor: 'rgba(16,185,129,0.34)',
		haloColor: 'rgba(110,231,183,0.28)',
	},
	private: {
		key: 'private',
		iconKey: 'shield',
		background: 'linear-gradient(135deg, #60a5fa, #1d4ed8)',
		badgeBackground: 'linear-gradient(135deg, rgba(239,246,255,0.98), rgba(219,234,254,0.98))',
		badgeBorder: 'rgba(59,130,246,0.32)',
		textColor: '#1d4ed8',
		borderColor: 'rgba(59,130,246,0.4)',
		glowColor: 'rgba(37,99,235,0.32)',
		haloColor: 'rgba(147,197,253,0.28)',
	},
	corporate: {
		key: 'corporate',
		iconKey: 'briefcase',
		background: 'linear-gradient(135deg, #818cf8, #4338ca)',
		badgeBackground: 'linear-gradient(135deg, rgba(238,242,255,0.98), rgba(224,231,255,0.98))',
		badgeBorder: 'rgba(99,102,241,0.3)',
		textColor: '#4338ca',
		borderColor: 'rgba(99,102,241,0.38)',
		glowColor: 'rgba(79,70,229,0.3)',
		haloColor: 'rgba(165,180,252,0.26)',
	},
	institutional: {
		key: 'institutional',
		iconKey: 'building',
		background: 'linear-gradient(135deg, #f59e0b, #d97706)',
		badgeBackground: 'linear-gradient(135deg, rgba(255,251,235,0.98), rgba(254,243,199,0.98))',
		badgeBorder: 'rgba(245,158,11,0.32)',
		textColor: '#b45309',
		borderColor: 'rgba(245,158,11,0.38)',
		glowColor: 'rgba(245,158,11,0.3)',
		haloColor: 'rgba(252,211,77,0.28)',
	},
	selfPay: {
		key: 'self-pay',
		iconKey: 'wallet',
		background: 'linear-gradient(135deg, #fb7185, #e11d48)',
		badgeBackground: 'linear-gradient(135deg, rgba(255,241,242,0.98), rgba(255,228,230,0.98))',
		badgeBorder: 'rgba(244,63,94,0.28)',
		textColor: '#be123c',
		borderColor: 'rgba(244,63,94,0.35)',
		glowColor: 'rgba(244,63,94,0.28)',
		haloColor: 'rgba(251,113,133,0.22)',
	},
	healthPlan: {
		key: 'health-plan',
		iconKey: 'heart',
		background: 'linear-gradient(135deg, #14b8a6, #0f766e)',
		badgeBackground: 'linear-gradient(135deg, rgba(240,253,250,0.98), rgba(204,251,241,0.98))',
		badgeBorder: 'rgba(20,184,166,0.28)',
		textColor: '#0f766e',
		borderColor: 'rgba(20,184,166,0.36)',
		glowColor: 'rgba(20,184,166,0.3)',
		haloColor: 'rgba(94,234,212,0.24)',
	},
	default: {
		key: 'default',
		iconKey: 'shield',
		background: 'linear-gradient(135deg, #38bdf8, #2563eb)',
		badgeBackground: 'linear-gradient(135deg, rgba(239,246,255,0.98), rgba(219,234,254,0.98))',
		badgeBorder: 'rgba(56,189,248,0.28)',
		textColor: '#1d4ed8',
		borderColor: 'rgba(56,189,248,0.36)',
		glowColor: 'rgba(37,99,235,0.28)',
		haloColor: 'rgba(125,211,252,0.24)',
	},
	uninsured: {
		key: 'uninsured',
		iconKey: 'off',
		background: 'linear-gradient(135deg, #94a3b8, #475569)',
		badgeBackground: 'linear-gradient(135deg, rgba(248,250,252,0.98), rgba(226,232,240,0.98))',
		badgeBorder: 'rgba(148,163,184,0.3)',
		textColor: '#475569',
		borderColor: 'rgba(148,163,184,0.34)',
		glowColor: 'rgba(100,116,139,0.24)',
		haloColor: 'rgba(203,213,225,0.22)',
	},
};

function normalizeInsuranceText(value: string | null | undefined): string {
	return String(value ?? '')
		.toLowerCase()
		.replace(/[_-]+/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
}

function isHexColor(value: string | null | undefined): value is string {
	return typeof value === 'string' && /^#[0-9a-fA-F]{6}$/.test(value);
}

function hexToRgb(value: string): [number, number, number] {
	const normalized = value.replace('#', '');
	return [
		Number.parseInt(normalized.slice(0, 2), 16),
		Number.parseInt(normalized.slice(2, 4), 16),
		Number.parseInt(normalized.slice(4, 6), 16),
	];
}

function withAlpha(value: string, alpha: number): string {
	if (!isHexColor(value)) {
		return `rgba(37,99,235,${alpha})`;
	}
	const [red, green, blue] = hexToRgb(value);
	return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function mixWithWhite(value: string, ratio: number): string {
	if (!isHexColor(value)) {
		return value;
	}
	const [red, green, blue] = hexToRgb(value);
	const mixed = [red, green, blue].map((channel) => Math.round(channel + (255 - channel) * ratio));
	return `rgb(${mixed[0]}, ${mixed[1]}, ${mixed[2]})`;
}

function resolveIconKey(value: InsurancePolicy['icon_key'] | null | undefined): InsuranceIconKey {
	const fallback: InsuranceIconKey = 'shield';
	return value ?? fallback;
}

function buildConfiguredVisual(policy: InsurancePolicy, label: string): InsuranceVisual | null {
	if (!isHexColor(policy.color_primary) && !isHexColor(policy.color_secondary) && !policy.icon_key) {
		return null;
	}

	const primary = isHexColor(policy.color_primary) ? policy.color_primary : '#60A5FA';
	const secondary = isHexColor(policy.color_secondary) ? policy.color_secondary : '#1D4ED8';
	const iconKey = resolveIconKey(policy.icon_key);

	return {
		key: `configured-${normalizeInsuranceText(label) || 'insurance'}`,
		label,
		iconKey,
		badgeText: String(policy.custom_badge_symbol ?? '').trim().toUpperCase() || null,
		background: `linear-gradient(135deg, ${primary}, ${secondary})`,
		badgeBackground: `linear-gradient(135deg, ${mixWithWhite(primary, 0.88)}, ${mixWithWhite(secondary, 0.8)})`,
		badgeBorder: withAlpha(primary, 0.34),
		textColor: secondary,
		borderColor: withAlpha(primary, 0.44),
		glowColor: withAlpha(secondary, 0.34),
		haloColor: withAlpha(primary, 0.24),
	};
}

function resolveInsuranceBucket(value: string): InsuranceBucket {
	const normalized = normalizeInsuranceText(value);

	if (!normalized || normalized.includes('no insurance') || normalized.includes('uninsured')) {
		return INSURANCE_BUCKETS.uninsured;
	}

	if (
		normalized.includes('self pay') ||
		normalized.includes('cash') ||
		normalized.includes('walk in') ||
		normalized.includes('out of pocket')
	) {
		return INSURANCE_BUCKETS.selfPay;
	}

	if (
		normalized.includes('government') ||
		normalized.includes('govt') ||
		normalized.includes('scheme') ||
		normalized.includes('ayushman') ||
		normalized.includes('esi') ||
		normalized.includes('cg') ||
		normalized.includes('medicare')
	) {
		return INSURANCE_BUCKETS.government;
	}

	if (
		normalized.includes('corporate') ||
		normalized.includes('company') ||
		normalized.includes('employee') ||
		normalized.includes('employer')
	) {
		return INSURANCE_BUCKETS.corporate;
	}

	if (
		normalized.includes('institution') ||
		normalized.includes('college') ||
		normalized.includes('student') ||
		normalized.includes('university') ||
		normalized.includes('saveetha')
	) {
		return INSURANCE_BUCKETS.institutional;
	}

	if (
		normalized.includes('health') ||
		normalized.includes('family') ||
		normalized.includes('floater') ||
		normalized.includes('mediclaim')
	) {
		return INSURANCE_BUCKETS.healthPlan;
	}

	if (
		normalized.includes('private') ||
		normalized.includes('policy') ||
		normalized.includes('insurance') ||
		normalized.includes('cover')
	) {
		return INSURANCE_BUCKETS.private;
	}

	return INSURANCE_BUCKETS.default;
}

function getInsuranceLabel(policy: InsurancePolicy): string | null {
	const coverageType = String(policy.coverage_type ?? '').trim();
	if (coverageType) {
		return coverageType;
	}

	const provider = String(policy.provider ?? '').trim();
	return provider || null;
}

export function getInsuranceVisuals(
	insurancePolicies?: InsurancePolicy[] | null,
	fallbackLabel?: string | null
): InsuranceVisual[] {
	const seen = new Set<string>();
	const visuals: InsuranceVisual[] = [];

	for (const policy of insurancePolicies ?? []) {
		const label = getInsuranceLabel(policy);
		if (!label) {
			continue;
		}

		const dedupeKey = `${normalizeInsuranceText(label)}|${normalizeInsuranceText(policy.provider)}`;
		if (seen.has(dedupeKey)) {
			continue;
		}
		seen.add(dedupeKey);

		const configuredVisual = buildConfiguredVisual(policy, label);
		if (configuredVisual) {
			visuals.push(configuredVisual);
			continue;
		}

		const bucket = resolveInsuranceBucket(`${label} ${policy.provider ?? ''}`);
		visuals.push({ ...bucket, label, badgeText: null });
	}

	if (!visuals.length && fallbackLabel?.trim()) {
		const bucket = resolveInsuranceBucket(fallbackLabel);
		visuals.push({ ...bucket, label: fallbackLabel.trim(), badgeText: null });
	}

	if (!visuals.length) {
		visuals.push({ ...INSURANCE_BUCKETS.uninsured, label: 'No insurance', badgeText: null });
	}

	return visuals;
}

export function getPrimaryInsuranceVisual(
	insurancePolicies?: InsurancePolicy[] | null,
	fallbackLabel?: string | null
): InsuranceVisual {
	return getInsuranceVisuals(insurancePolicies, fallbackLabel)[0];
}