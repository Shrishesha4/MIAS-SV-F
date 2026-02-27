<script lang="ts">
  import type { Snippet } from 'svelte';
  import { X } from 'lucide-svelte';

  interface Props {
    open: boolean;
    title?: string;
    onclose: () => void;
    children: Snippet;
  }

  let { open = $bindable(false), title = '', onclose, children }: Props = $props();
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    style="background-color: rgba(0,0,0,0.5);"
    onkeydown={(e) => e.key === 'Escape' && onclose()}
  >
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="absolute inset-0" onclick={onclose}></div>
    <div
      class="relative w-full max-w-md animate-slide-up"
      style="background-color: white;
             border-radius: 10px;
             box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24),
                         0 0 0 1px rgba(0,0,0,0.05), inset 0 -5px 10px rgba(0,0,0,0.05);
             border: 1px solid rgba(0,0,0,0.1);"
    >
      {#if title}
        <div
          class="px-4 py-3 flex items-center justify-between"
          style="background-image: linear-gradient(to bottom, #f8f9fb, #d9e1ea);
                 box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1);
                 border-bottom: 1px solid rgba(0,0,0,0.1);
                 border-radius: 10px 10px 0 0;"
        >
          <h3 class="text-blue-900 font-semibold" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
            {title}
          </h3>
          <button class="text-gray-500 hover:text-gray-700 cursor-pointer" onclick={onclose}>
            <X class="w-5 h-5" />
          </button>
        </div>
      {/if}
      <div class="p-4">
        {@render children()}
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideUp {
    from { transform: translateY(20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
  .animate-slide-up {
    animation: slideUp 0.3s ease-out;
  }
</style>
