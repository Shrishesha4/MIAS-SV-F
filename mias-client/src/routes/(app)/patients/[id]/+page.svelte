<script lang="ts">
	import { page } from '$app/state';
	import PatientProfile from '$lib/components/PatientProfile.svelte';
</script>

<PatientProfile patientId={page.params.id ?? ''} canEdit={page.url.searchParams.get('mode') !== 'view'} />
