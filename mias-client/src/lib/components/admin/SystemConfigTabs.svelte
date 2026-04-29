<script lang="ts">
	import { goto } from '$app/navigation';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { BrainCircuit, UsersRound, CreditCard, FileText, DatabaseBackup, MapPin, ClipboardCheck } from 'lucide-svelte';

	interface Props {
		activeTab: 'patients' | 'icd' | 'ai' | 'insurance' | 'backup' | 'geofencing' | 'attendance';
	}

	let { activeTab }: Props = $props();

	const tabs = [
		{ id: 'patients', label: 'Patients', icon: UsersRound },
		{ id: 'icd', label: 'ICD Codes', icon: FileText },
		{ id: 'insurance', label: 'Insurance', icon: CreditCard },
		{ id: 'ai', label: 'AI', icon: BrainCircuit },
		{ id: 'attendance', label: 'Attendance Logs', icon: ClipboardCheck },
		{ id: 'backup', label: 'Backup & Restore', icon: DatabaseBackup },
		{ id: 'geofencing', label: 'Geofencing', icon: MapPin },
	];
</script>

<TabBar
	tabs={tabs}
	activeTab={activeTab}
	variant="jiggle"
	stretch={false}
	ariaLabel="System config tabs"
	onchange={(tabId) => goto(`/admin/system/${tabId}`)}
/>
