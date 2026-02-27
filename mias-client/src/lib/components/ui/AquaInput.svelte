<script lang="ts">
  interface Props {
    type?: string;
    placeholder?: string;
    value?: string;
    name?: string;
    icon?: any;
    oninput?: (e: Event) => void;
    onchange?: (e: Event) => void;
  }

  let {
    type = 'text',
    placeholder = '',
    value = $bindable(''),
    name = '',
    icon: Icon = null,
    oninput,
    onchange,
  }: Props = $props();
</script>

<div
  class="flex items-center px-4 py-3"
  style="border: 1px solid rgba(0,0,0,0.2);
         border-radius: 6px;
         background-color: rgba(255,255,255,0.8);
         box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"
>
  {#if Icon}
    <Icon class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
  {/if}
  <input
    {type}
    {placeholder}
    {name}
    bind:value
    class="flex-1 outline-none text-gray-700 bg-transparent"
    {oninput}
    {onchange}
  />
</div>
