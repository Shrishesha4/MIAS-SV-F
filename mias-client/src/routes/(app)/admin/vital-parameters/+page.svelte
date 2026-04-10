<script lang="ts">
	import AdminScaffold from '$lib/components/layout/AdminScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
    import { Heart } from "lucide-svelte"; 

</script>


<AdminScaffold
	title="Vital Parameters"
	titleIcon={Heart}
	navItems={adminPageNavItems}
	activeNav="vital_parameters"
	backHref="/admin"
>   
    <div class="p-6">
        <h2 class="text-2xl font-semibold mb-4">Manage Vital Parameters</h2>
        <p class="text-gray-600 mb-6">Add, edit, or remove vital parameters used for patient monitoring.</p>
        <!-- Content for managing vital parameters goes here -->
    </div>
</AdminScaffold>