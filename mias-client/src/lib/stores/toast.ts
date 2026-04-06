import { writable } from 'svelte/store';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
	id: string;
	message: string;
	type: ToastType;
}

function createToastStore() {
	const { subscribe, update } = writable<Toast[]>([]);

	function addToast(message: string, type: ToastType = 'info') {
		const id = crypto.randomUUID();
		update(toasts => [...toasts, { id, message, type }]);
		setTimeout(() => removeToast(id), 4000);
		return id;
	}

	function removeToast(id: string) {
		update(toasts => toasts.filter(t => t.id !== id));
	}

	return { subscribe, addToast, removeToast };
}

export const toastStore = createToastStore();
