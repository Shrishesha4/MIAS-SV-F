<script lang="ts">
  import { cubicOut } from 'svelte/easing';
  import { fade, fly } from 'svelte/transition';
  import { goto } from '$app/navigation';
  import { authStore, userRole } from '$lib/stores/auth';
  import { getMenuItems } from '$lib/config/menuItems';
  import Avatar from '../ui/Avatar.svelte';
  import { X, LogOut } from 'lucide-svelte';

  interface Props {
    open: boolean;
    onclose: () => void;
    userName?: string;
    userRole?: string;
    userId?: string;
  }

  let {
    open = $bindable(false),
    onclose,
    userName = '',
    userRole: role = '',
    userId = '',
  }: Props = $props();

  const menuItems = $derived(getMenuItems(role));

  function navigate(path: string) {
    goto(path);
    onclose();
  }

  function logout() {
    authStore.logout();
    goto('/login');
    onclose();
  }
</script>

{#if open}
  <!-- Backdrop -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="fixed inset-0 z-50" onkeydown={(e) => e.key === 'Escape' && onclose()}>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
      class="motion-overlay absolute inset-0"
      style="background-color: rgba(0,0,0,0.5);"
      onclick={onclose}
      transition:fade={{ duration: 180 }}
    ></div>

    <!-- Side panel -->
    <div
      class="motion-drawer absolute top-0 right-0 bottom-0 w-72"
      style="background-image: repeating-linear-gradient(
               0deg,
               rgba(180, 190, 210, 0.2),
               rgba(180, 190, 210, 0.2) 1px,
               rgba(210, 220, 230, 0.4) 1px,
               rgba(210, 220, 230, 0.4) 2px
                  );
                  background-color: #e0e5eb;"
                in:fly={{ x: 24, duration: 280, easing: cubicOut }}
                out:fly={{ x: 18, duration: 180 }}
    >
      <!-- Header -->
      <div
        class="px-4 py-4 flex items-center justify-between"
        style="background-image: linear-gradient(to bottom, #d1dbed, #b8c6df);
               border-bottom: 1px solid rgba(0,0,0,0.2);"
      >
        <div class="flex items-center gap-3">
          <Avatar name={userName} size="sm" />
          <div>
            <p class="text-blue-900 font-semibold text-sm" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
              {userName}
            </p>
            <p class="text-blue-700 text-xs">{userId}</p>
          </div>
        </div>
        <button class="motion-control text-blue-800 cursor-pointer" onclick={onclose}>
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Menu Items -->
      <div class="py-2 overflow-y-auto" style="max-height: calc(100vh - 140px);">
        {#each menuItems as item}
          {@const Icon = item.icon}
          <button
            class="motion-list-item w-full flex items-center gap-3 px-4 py-3 text-left text-blue-800 hover:bg-white/50 transition-colors cursor-pointer"
            style="text-shadow: 0 1px 0 rgba(255,255,255,0.5);"
            onclick={() => navigate(item.path)}
          >
            <Icon class="w-5 h-5" />
            <span class="text-sm font-medium">{item.label}</span>
          </button>
        {/each}
      </div>

      <!-- Logout -->
      <div class="absolute bottom-0 left-0 right-0 p-4" style="border-top: 1px solid rgba(0,0,0,0.1);">
        <button
           class="motion-control w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-white font-medium cursor-pointer
                 relative overflow-hidden transition-all active:translate-y-0.5"
          style="background: linear-gradient(to bottom, #ff5a5a, #cc0000);
                 border: 1px solid rgba(0,0,0,0.2);
                 box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);"
          onclick={logout}
        >
          <LogOut class="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  </div>
{/if}
