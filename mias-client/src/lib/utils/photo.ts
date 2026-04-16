const API_ORIGIN = import.meta.env.VITE_API_URL?.replace('/api/v1', '') || 'http://localhost:8001';

export function resolvePhotoSrc(photo?: string | null): string | null {
	if (!photo) return null;
	const value = photo.trim();
	if (!value) return null;
	if (
		value.startsWith('data:') ||
		value.startsWith('blob:') ||
		value.startsWith('http://') ||
		value.startsWith('https://')
	) {
		return value;
	}
	if (value.startsWith('//')) {
		return `https:${value}`;
	}
	if (value.startsWith('/')) {
		return `${API_ORIGIN}${value}`;
	}
	return value;
}
