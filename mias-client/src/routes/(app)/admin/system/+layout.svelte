<script lang="ts">
	import { page } from '$app/state';
	import { fly } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import SystemConfigTabs from '$lib/components/admin/SystemConfigTabs.svelte';

	let { children } = $props();

	type TabId = 'patients' | 'icd' | 'insurance' | 'ai' | 'backup' | 'geofencing';
	const TABS: TabId[] = ['patients', 'icd', 'insurance', 'ai', 'backup', 'geofencing'];

	const currentTab = $derived<TabId>((TABS.includes(page.url.pathname.split('/').pop() as TabId) ? page.url.pathname.split('/').pop() : 'patients') as TabId);
	const currentIdx = $derived(Math.max(0, TABS.indexOf(currentTab)));

	let prevIdx = $state(0);
	let slideDir = $state(1);

	$effect.pre(() => {
		const curr = currentIdx;
		slideDir = curr >= prevIdx ? 1 : -1;
		prevIdx = curr;
	});

	function tabExit(node: HTMLElement) {
		node.style.position = 'absolute';
		node.style.inset = '0';
		node.style.zIndex = '0';
		node.style.pointerEvents = 'none';
		node.style.overflow = 'hidden';
		return {
			duration: 130,
			css: (t: number) => `opacity: ${t * 0.25};`
		};
	}
</script>

<!-- Tab bar is static — outside the key block so it never transitions -->
<div class="space-y-4">
	<div
		class="rounded-3xl border border-slate-200 p-3"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.92), rgba(246,249,255,0.92)); box-shadow: 0 10px 24px rgba(15,23,42,0.05);"
	>
		<SystemConfigTabs activeTab={currentTab} />
	</div>

	<div class="system-tab-content">
		{#key currentTab}
			<div
				class="system-tab-page"
				in:fly={{ x: slideDir * 26, duration: 260, easing: cubicOut, opacity: 0 }}
				out:tabExit
			>
				{@render children()}
			</div>
		{/key}
	</div>
</div>

<style>
	.system-tab-content {
		position: relative;
		overflow-x: hidden;
	}

	.system-tab-page {
		position: relative;
		width: 100%;
	}
</style>
