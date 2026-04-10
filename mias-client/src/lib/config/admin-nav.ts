import { BarChart3, BrainCircuit, Building2, FlaskConical, GraduationCap, Shield, Stethoscope, Users, IndianRupee, FileText } from 'lucide-svelte';

export const adminPageNavItems = [
	{ id: 'clinics', label: 'Clinics', href: '/admin/clinics', icon: Building2 },
	{ id: 'labs', label: 'Labs', href: '/admin/labs', icon: FlaskConical },
	{ id: 'charges', label: 'Charges', href: '/admin/charges', icon: IndianRupee },
	{ id: 'forms', label: 'Forms', href: '/admin/forms', icon: FileText },
	{ id: 'ai', label: 'AI', href: '/admin/ai', icon: BrainCircuit },
	{ id: 'users', label: 'Users', href: '/admin/users', icon: Users },
	{ id: 'departments', label: 'Depts', href: '/admin/departments', icon: Stethoscope },
	{ id: 'programmes', label: 'Programs', href: '/admin/programmes', icon: GraduationCap },
	{ id: 'analytics', label: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
];