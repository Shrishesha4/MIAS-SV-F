<script lang="ts">
  interface Tab {
    id: string;
    label: string;
    icon?: any;
  }

  interface Props {
    tabs: Tab[];
    activeTab: string;
    onchange: (tabId: string) => void;
  }

  let { tabs, activeTab, onchange }: Props = $props();
</script>

<div
  class="motion-surface flex rounded-xl overflow-hidden"
  style="background-color: white;
         border-radius: 10px;
         box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
         border: 1px solid rgba(0,0,0,0.1);"
>
  {#each tabs as tab (tab.id)}
    <button
      class="motion-control flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-sm font-medium cursor-pointer transition-all relative"
      class:active-tab={activeTab === tab.id}
      class:inactive-tab={activeTab !== tab.id}
      onclick={() => onchange(tab.id)}
    >
      {#if tab.icon}
        {@const Icon = tab.icon}
        <Icon class="w-4 h-4" />
      {/if}
      <span>{tab.label}</span>
      <div
        class="absolute bottom-0 left-2 right-2 h-0.5 rounded-full transition-all duration-300"
        style="background: #3b82f6; transform-origin: center; opacity: {activeTab === tab.id ? 1 : 0}; transform: scaleX({activeTab === tab.id ? 1 : 0.35});"
      ></div>
    </button>
  {/each}
</div>

<style>
  .active-tab {
    color: #2563eb;
    background-color: rgba(59, 130, 246, 0.05);
  }
  .inactive-tab {
    color: #6b7280;
  }
  .inactive-tab:hover {
    color: #374151;
    background-color: rgba(0, 0, 0, 0.02);
  }
</style>
