<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { get } from 'svelte/store';

	onMount(() => {
		const auth = get(authStore);
		if (auth.isAuthenticated) {
			if (auth.role === 'STUDENT') {
				goto('/patients');
			} else if (auth.role === 'ACADEMIC_MANAGER') {
				goto('/academic-manager');
			} else {
				goto('/dashboard');
			}
		} else {
			goto('/login');
		}
	});
</script>

<div class="flex items-center justify-center min-h-screen">
	<div class="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
</div>
