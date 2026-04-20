<script lang="ts">
	import { goto } from '$app/navigation';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { BrainCircuit, UsersRound, CreditCard, FileText, Stethoscope } from 'lucide-svelte';

	interface Props {
		activeTab: 'patients' | 'icd' | 'ai' | 'insurance' | 'ot';
	}

	let { activeTab }: Props = $props();

	const tabs = [
		{ id: 'patients', label: 'Patients', icon: UsersRound },
		{ id: 'icd', label: 'ICD Codes', icon: FileText },
		{ id: 'insurance', label: 'Insurance', icon: CreditCard },
		{ id: 'ai', label: 'AI', icon: BrainCircuit },
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
