import { goto } from '$app/navigation';
import { get } from 'svelte/store';
import { authStore } from '$lib/stores/auth';

export function checkRoleAccess(allowedRoles: string[]): boolean {
	const { role } = get(authStore);
	return !!role && allowedRoles.includes(role);
}

export function redirectIfUnauthorized(allowedRoles: string[], fallbackPath = '/dashboard') {
	if (!checkRoleAccess(allowedRoles)) {
		goto(fallbackPath);
		return false;
	}
	return true;
}
