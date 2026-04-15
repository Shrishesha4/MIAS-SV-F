const highlightedKeywords = ['ELITE', 'VIP', 'PRIME', 'PREMIUM'];

export type PatientCategoryVisual = {
	label: string;
	background: string;
	borderColor: string;
	glowColor: string;
	haloColor: string;
};

const CATEGORY_PRESETS: Record<string, { primary: string; secondary: string }> = {
	classic: { primary: '#60A5FA', secondary: '#1D4ED8' },
	prime: { primary: '#A78BFA', secondary: '#6D28D9' },
	elite: { primary: '#FBBF24', secondary: '#D97706' },
	community: { primary: '#34D399', secondary: '#047857' },
	default: { primary: '#60A5FA', secondary: '#1D4ED8' },
};

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

function resolveCategoryColors(category?: string | null, primary?: string | null, secondary?: string | null) {
	if (isHexColor(primary) && isHexColor(secondary)) {
		return { primary, secondary };
	}

	const normalized = (category || '').trim().toLowerCase();
	return CATEGORY_PRESETS[normalized] || CATEGORY_PRESETS.default;
}

export function isHighlightedPatientCategory(category?: string | null): boolean {
	const normalized = (category || '').trim().toUpperCase();
	return highlightedKeywords.some((keyword) => normalized.includes(keyword));
}

export function formatPatientCategoryLabel(category?: string | null): string {
	const normalized = (category || '').trim();
	if (!normalized) {
		return 'Unassigned';
	}

	if (normalized === normalized.toUpperCase() && normalized.length <= 4) {
		return normalized;
	}

	return normalized
		.replace(/[_-]+/g, ' ')
		.split(/\s+/)
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
		.join(' ');
}

export function getPatientCategoryVisual(
	category?: string | null,
	primary?: string | null,
	secondary?: string | null
): PatientCategoryVisual {
	const colors = resolveCategoryColors(category, primary, secondary);
	return {
		label: formatPatientCategoryLabel(category),
		background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`,
		borderColor: withAlpha(colors.primary, 0.44),
		glowColor: withAlpha(colors.secondary, 0.34),
		haloColor: withAlpha(colors.primary, 0.26),
	};
}