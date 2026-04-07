<script lang="ts">
  import { ArrowLeft, Menu, Bell, HeartPulse, Search, X } from 'lucide-svelte';
  import { goto } from '$app/navigation';
  import { patientApi } from '$lib/api/patients';

  interface Props {
    showBack?: boolean;
    showMenu?: boolean;
    showNotifications?: boolean;
    notificationCount?: number;
    onmenuclick?: () => void;
    onmenuenter?: () => void;
    onmenuleave?: () => void;
  }

  let {
    showBack = false,
    showMenu = true,
    showNotifications = true,
    notificationCount = 0,
    onmenuclick,
    onmenuenter,
    onmenuleave,
  }: Props = $props();

  // Patient search state
  let searchQuery = $state('');
  let searchResults = $state<any[]>([]);
  let searchOpen = $state(false);
  let searching = $state(false);
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;
  let searchInputRef = $state<HTMLInputElement | null>(null);

  function goBack() {
    history.back();
  }

  function handleSearchInput() {
    if (debounceTimer) clearTimeout(debounceTimer);
    if (!searchQuery.trim()) {
      searchResults = [];
      searchOpen = false;
      return;
    }
    debounceTimer = setTimeout(async () => {
      if (!searchQuery.trim()) return;
      searching = true;
      try {
        searchResults = await patientApi.searchPatientsForAdmission(searchQuery.trim());
        searchOpen = true;
      } catch {
        searchResults = [];
      } finally {
        searching = false;
      }
    }, 300);
  }

  function selectPatient(patient: any) {
    goto(`/patients/${patient.id}`);
    searchQuery = '';
    searchResults = [];
    searchOpen = false;
  }

  function clearSearch() {
    searchQuery = '';
    searchResults = [];
    searchOpen = false;
  }

  function handleSearchBlur() {
    // Delay closing to allow click on results
    setTimeout(() => { searchOpen = false; }, 200);
  }
</script>

<nav
  class="sticky top-0 z-40 px-3 py-2.5 flex items-center justify-between"
  style="background-image: linear-gradient(to bottom, #4a7cc9, #3568b2);
         box-shadow: 0 2px 6px rgba(0,0,0,0.25);
         border-bottom: 1px solid rgba(0,0,0,0.15);"
>
  <div class="flex items-center gap-2.5 shrink-0">
    <!-- {#if showBack}
      <button class="text-white/90 cursor-pointer hover:text-white transition-colors" onclick={goBack}>
        <ArrowLeft class="w-5 h-5" />
      </button>
    {/if} -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      role="button"
      tabindex="0"
      class="w-9 h-9 rounded-full flex items-center justify-center cursor-pointer"
      style="background: linear-gradient(to bottom, #5a8ed6, #3a6bb5);
             border: 1.5px solid rgba(255,255,255,0.3);
             box-shadow: 0 1px 3px rgba(0,0,0,0.3);"
      onmouseenter={onmenuenter}
      onmouseleave={onmenuleave}
    >
      <HeartPulse class="w-4.5 h-4.5 text-white" />
    </div>
    <div class="leading-tight hidden sm:block">
      <p class="text-white font-bold text-sm tracking-tight">Saveetha Medical</p>
      <p class="text-white/75 text-[11px] font-medium">College Hospital</p>
    </div>
  </div>

  <!-- Patient Search (desktop only) -->
  <div class="hidden md:block flex-1 max-w-sm mx-4 relative">
    <div class="relative">
      <Search class="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none" />
      <input
        bind:this={searchInputRef}
        type="text"
        placeholder="Search patients..."
        bind:value={searchQuery}
        oninput={handleSearchInput}
        onfocus={() => { if (searchResults.length) searchOpen = true; }}
        onblur={handleSearchBlur}
        class="w-full pl-9 pr-8 py-1.5 text-sm rounded-lg outline-none text-white placeholder-white/50"
        style="background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.2);
               backdrop-filter: blur(4px);"
      />
      {#if searchQuery}
        <button class="absolute right-2 top-1/2 -translate-y-1/2 text-white/50 hover:text-white cursor-pointer" onclick={clearSearch}>
          <X class="w-3.5 h-3.5" />
        </button>
      {/if}
    </div>

    <!-- Search dropdown -->
    {#if searchOpen && searchResults.length > 0}
      <div
        class="absolute left-0 right-0 top-full mt-1 rounded-lg overflow-hidden max-h-64 overflow-y-auto z-50"
        style="background: white; border: 1px solid rgba(0,0,0,0.12);
               box-shadow: 0 4px 12px rgba(0,0,0,0.15);"
      >
        {#each searchResults as patient}
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            class="px-3 py-2 cursor-pointer hover:bg-blue-50 flex items-center gap-3 transition-colors"
            style="border-bottom: 1px solid rgba(0,0,0,0.06);"
            onclick={() => selectPatient(patient)}
          >
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
                 style="background: linear-gradient(to bottom, #4d90fe, #3b7aed);">
              {patient.name?.charAt(0) ?? '?'}
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium text-gray-800 truncate">{patient.name}</p>
              <p class="text-xs text-gray-500">{patient.patient_id}{patient.gender ? ` · ${patient.gender}` : ''}{patient.blood_group ? ` · ${patient.blood_group}` : ''}</p>
            </div>
          </div>
        {/each}
      </div>
    {:else if searchOpen && searchQuery.trim() && !searching}
      <div
        class="absolute left-0 right-0 top-full mt-1 rounded-lg overflow-hidden z-50 p-4 text-center text-sm text-gray-500"
        style="background: white; border: 1px solid rgba(0,0,0,0.12);
               box-shadow: 0 4px 12px rgba(0,0,0,0.15);"
      >
        No patients found
      </div>
    {/if}
  </div>

  <div class="flex items-center gap-2 shrink-0">
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
        class="w-9 h-9 rounded-full flex items-center justify-center cursor-pointer transition-colors md:hidden"
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
