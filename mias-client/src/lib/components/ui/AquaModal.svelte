<script lang="ts">
  import type { Snippet } from 'svelte';
  import { X } from 'lucide-svelte';

  interface Props {
    open?: boolean;
    title?: string;
    onclose?: () => void;
    onClose?: () => void;  // Alternative prop name
    header?: Snippet;
    children: Snippet;
  }

  let { open = true, title = '', onclose, onClose, header, children }: Props = $props();

  const handleClose = () => {
    if (onclose) onclose();
    if (onClose) onClose();
  };
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
    style="background-color: rgba(0,0,0,0.5);"
    onkeydown={(e) => e.key === 'Escape' && handleClose()}
  >
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="absolute inset-0" onclick={handleClose}></div>
    <div
      class="relative w-full sm:max-w-md max-h-[90vh] flex flex-col animate-slide-up"
      style="background-color: white;
             border-radius: 16px 16px 0 0;
             box-shadow: 0 -4px 20px rgba(0,0,0,0.15);
             border: 1px solid rgba(0,0,0,0.1);"
    >
      <!-- Header -->
      <div
        class="px-4 py-3 flex items-center justify-between z-10 shrink-0"
        style="background-image: linear-gradient(to bottom, #f8f9fb, #e8eef5);
               box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1);
               border-bottom: 1px solid rgba(0,0,0,0.1);
               border-radius: 16px 16px 0 0;"
      >
        {#if header}
          <div class="flex-1">
            {@render header()}
          </div>
        {:else if title}
          <h3 class="text-blue-900 font-semibold" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
            {title}
          </h3>
        {:else}
          <div></div>
        {/if}
        <button class="text-gray-500 hover:text-gray-700 cursor-pointer ml-2" onclick={handleClose}>
          <X class="w-5 h-5" />
        </button>
      </div>
      <div class="p-4 overflow-y-auto flex-1">
        {@render children()}
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideUp {
    from { transform: translateY(100%); opacity: 0.5; }
    to { transform: translateY(0); opacity: 1; }
  }
  .animate-slide-up {
    animation: slideUp 0.3s ease-out;
  }
  
  @media (min-width: 640px) {
    .animate-slide-up {
      border-radius: 16px !important;
    }
  }
</style>
