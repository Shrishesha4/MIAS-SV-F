<script lang="ts">
  import type { Snippet } from 'svelte';
  import { cubicOut } from 'svelte/easing';
  import { fade, fly } from 'svelte/transition';
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
    class="fixed inset-0 z-50 flex items-end sm:items-center justify-center motion-overlay"
    style="background-color: rgba(0,0,0,0.5);"
    onkeydown={(e) => e.key === 'Escape' && handleClose()}
    transition:fade={{ duration: 180 }}
  >
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="absolute inset-0" onclick={handleClose}></div>
    <div
      class="motion-dialog relative w-full sm:max-w-md max-h-[90vh] flex flex-col"
      style="background-color: white;
             border-radius: 16px 16px 0 0;
             box-shadow: 0 -4px 20px rgba(0,0,0,0.15);
             border: 1px solid rgba(0,0,0,0.1);"
      in:fly={{ y: 24, duration: 280, easing: cubicOut }}
      out:fly={{ y: 18, duration: 180 }}
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
        <button class="motion-control text-gray-500 hover:text-gray-700 cursor-pointer ml-2" onclick={handleClose}>
          <X class="w-5 h-5" />
        </button>
      </div>
      <div class="p-4 overflow-y-auto flex-1">
        {@render children()}
      </div>
    </div>
  </div>
{/if}
