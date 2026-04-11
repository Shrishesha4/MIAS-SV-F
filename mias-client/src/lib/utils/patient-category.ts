const highlightedKeywords = ['ELITE', 'VIP', 'PRIME', 'PREMIUM'];

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