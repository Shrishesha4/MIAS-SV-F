<script lang="ts">
  import { ArrowLeft, Menu, Bell, HeartPulse } from 'lucide-svelte';
  import { goto } from '$app/navigation';

  interface Props {
    showBack?: boolean;
    showMenu?: boolean;
    showNotifications?: boolean;
    notificationCount?: number;
    onmenuclick?: () => void;
  }

  let {
    showBack = false,
    showMenu = true,
    showNotifications = true,
    notificationCount = 0,
    onmenuclick,
  }: Props = $props();

  function goBack() {
    history.back();
  }
</script>

<nav
  class="sticky top-0 z-40 px-3 py-2.5 flex items-center justify-between"
  style="background-image: linear-gradient(to bottom, #4a7cc9, #3568b2);
         box-shadow: 0 2px 6px rgba(0,0,0,0.25);
         border-bottom: 1px solid rgba(0,0,0,0.15);"
>
  <div class="flex items-center gap-2.5">
    {#if showBack}
      <button class="text-white/90 cursor-pointer hover:text-white transition-colors" onclick={goBack}>
        <ArrowLeft class="w-5 h-5" />
      </button>
    {/if}
    <div
      class="w-9 h-9 rounded-full flex items-center justify-center"
      style="background: linear-gradient(to bottom, #5a8ed6, #3a6bb5);
             border: 1.5px solid rgba(255,255,255,0.3);
             box-shadow: 0 1px 3px rgba(0,0,0,0.3);"
    >
      <HeartPulse class="w-4.5 h-4.5 text-white" />
    </div>
    <div class="leading-tight">
      <p class="text-white font-bold text-sm tracking-tight">Saveetha Medical</p>
      <p class="text-white/75 text-[11px] font-medium">College Hospital</p>
    </div>
  </div>

  <div class="flex items-center gap-2">
    {#if showNotifications}
      <button
        class="relative w-9 h-9 rounded-full flex items-center justify-center cursor-pointer transition-colors"
        style="background: linear-gradient(to bottom, #5a8ed6, #3a6bb5);
               border: 1.5px solid rgba(255,255,255,0.3);
               box-shadow: 0 1px 3px rgba(0,0,0,0.3);"
        onclick={() => goto('/notifications')}
      >
        <Bell class="w-4 h-4 text-white" />
        {#if notificationCount > 0}
          <span
            class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full text-white text-[10px] font-bold px-1"
            style="background: linear-gradient(to bottom, #ff3b30, #d70015);
                   border: 1.5px solid #3a6bb5;
                   animation: notificationPulse 2s infinite;"
          >
            {notificationCount > 9 ? '9+' : notificationCount}
          </span>
        {/if}
      </button>
    {/if}

    {#if showMenu}
      <button
        class="w-9 h-9 rounded-full flex items-center justify-center cursor-pointer transition-colors"
        style="background: linear-gradient(to bottom, #5a8ed6, #3a6bb5);
               border: 1.5px solid rgba(255,255,255,0.3);
               box-shadow: 0 1px 3px rgba(0,0,0,0.3);"
        onclick={onmenuclick}
      >
        <Menu class="w-4 h-4 text-white" />
      </button>
    {/if}
  </div>
</nav>

<style>
  @keyframes notificationPulse {
    0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
    70% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(255, 0, 0, 0); }
    100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
  }
</style>
