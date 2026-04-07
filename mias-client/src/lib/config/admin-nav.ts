import { BarChart3, GraduationCap, Shield, Stethoscope, Users } from 'lucide-svelte';

export const adminPageNavItems = [
	{ id: 'overview', label: 'Dashboard', href: '/admin', icon: Shield },
	{ id: 'users', label: 'Users', href: '/admin/users', icon: Users },
	{ id: 'departments', label: 'Depts', href: '/admin/departments', icon: Stethoscope },
	{ id: 'programmes', label: 'Programs', href: '/admin/programmes', icon: GraduationCap },
	{ id: 'analytics', label: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
];