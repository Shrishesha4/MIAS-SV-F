<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import AcademicWorkspace from '$lib/components/admin/AcademicWorkspace.svelte';
	import { authStore } from '$lib/stores/auth';

	const auth = get(authStore);

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			void goto(resolve('/dashboard'));
			return;
		}
	});
</script>

<AcademicWorkspace
	title="Academic Programmes"
	subtitle="Manage programmes, groups, targets, and academic weightage from one workspace."
/>
