export function normalizeChargeTierSpacing(value: string): string {
	return value.trim().replace(/\s*-\s*/g, ' - ').replace(/\s+/g, ' ');
}

export function normalizeChargeTierKey(value: string): string {
	return normalizeChargeTierSpacing(value).toLocaleLowerCase();
}

export function buildMappedChargeTierKey(insuranceName: string, patientCategoryName: string): string {
	return normalizeChargeTierSpacing(`${insuranceName} - ${patientCategoryName}`);
}

export function findCanonicalChargeTierEntry<T>(
	entries: Record<string, T>,
	tier: string
): { key: string; value: T } | null {
	const targetKey = normalizeChargeTierKey(tier);
	for (const [entryKey, entryValue] of Object.entries(entries || {})) {
		if (normalizeChargeTierKey(entryKey) === targetKey) {
			return { key: entryKey, value: entryValue };
		}
	}
	return null;
}
