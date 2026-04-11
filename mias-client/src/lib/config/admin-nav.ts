import { BarChart3, BrainCircuit, Building2, FlaskConical, GraduationCap, Stethoscope, Users, IndianRupee, FileText, Heart } from 'lucide-svelte';

export const adminPageNavItems = [
	{ id: 'clinics', label: 'Hospital Clinics', href: '/admin/clinics', icon: Building2 },
	{ id: 'departments', label: 'Medical Departments', href: '/admin/departments', icon: Stethoscope },
	{ id: 'system', label: 'System Config', href: '/admin/system/patients', icon: BrainCircuit },
	{ id: 'users', label: 'Manage Users', href: '/admin/users', icon: Users },
	{ id: 'labs', label: 'Laboratory Services', href: '/admin/labs', icon: FlaskConical },
	{ id: 'charges', label: 'Charge Master', href: '/admin/charges', icon: IndianRupee },
	{ id: 'programmes', label: 'Academics', href: '/admin/programmes', icon: GraduationCap },
	{ id: 'forms', label: 'Forms', href: '/admin/forms', icon: FileText },
	{ id: 'vital_parameters', label: 'Vital Parameters', href: '/admin/vital-parameters', icon: Heart },
	{ id: 'analytics', label: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
];