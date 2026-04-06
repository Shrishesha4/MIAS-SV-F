<script lang="ts">
	import { page } from '$app/state';
	import PatientProfile from '$lib/components/PatientProfile.svelte';
</script>

<PatientProfile patientId={page.params.id ?? ''} />
