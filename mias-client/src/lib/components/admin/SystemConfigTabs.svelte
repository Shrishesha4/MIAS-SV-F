<script lang="ts">
	import { goto } from '$app/navigation';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { BrainCircuit, UsersRound } from 'lucide-svelte';

	interface Props {
		activeTab: 'patients' | 'ai';
	}

	let { activeTab }: Props = $props();

	const tabs = [
		{ id: 'patients', label: 'Patients', icon: UsersRound },
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