const IST_TIME_ZONE = 'Asia/Kolkata';

export function formatDateTimeIST(
	value: string | number | Date,
	options: Intl.DateTimeFormatOptions = {}
): string {
	return new Date(value).toLocaleString('en-IN', {
		timeZone: IST_TIME_ZONE,
		...options,
	});
}

export function formatDateIST(
	value: string | number | Date,
	options: Intl.DateTimeFormatOptions = {}
): string {
	return new Date(value).toLocaleDateString('en-IN', {
		timeZone: IST_TIME_ZONE,
		...options,
	});
}

export function formatTimeIST(
	value: string | number | Date,
	options: Intl.DateTimeFormatOptions = {}
): string {
	return new Date(value).toLocaleTimeString('en-IN', {
		timeZone: IST_TIME_ZONE,
		...options,
	});
}

export function nowISTDate(
	options: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' }
): string {
	return formatDateIST(new Date(), options);
}

export function nowISTTime(
	options: Intl.DateTimeFormatOptions = { hour: '2-digit', minute: '2-digit' }
): string {
	return formatTimeIST(new Date(), options);
}
