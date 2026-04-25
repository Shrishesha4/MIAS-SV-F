import {
	Home, User, FileText, Clipboard, Pill, Activity,
	TestTube, Wallet, Bell, GraduationCap,
	Users, CheckCircle, Bed, Calendar, Building, BarChart3, Stethoscope, CreditCard, Cpu,
	Archive, Search, Download, FlaskConical, ChefHat, BookOpen, Landmark
} from 'lucide-svelte';

export interface MenuItem {
	icon: any;
	label: string;
	path: string;
}

export const patientMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/dashboard' },
	{ icon: User, label: 'Profile', path: '/profile' },
];

export const studentMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/dashboard' },
	{ icon: User, label: 'Profile', path: '/profile' },
	// { icon: Users, label: 'Assigned Patients', path: '/patients' },
	// { icon: Clipboard, label: 'Case Records', path: '/case-records' },
	// { icon: Bed, label: 'Admissions', path: '/admissions' },
	// { icon: Calendar, label: 'Clinic Sessions', path: '/clinic-sessions' },
	{ icon: Bell, label: 'Notifications', path: '/notifications' },
];

export const facultyMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/dashboard' },
	{ icon: User, label: 'Profile', path: '/profile' },
	// { icon: CheckCircle, label: 'Approvals', path: '/approvals' },
	{ icon: GraduationCap, label: 'Students', path: '/students' },
	// { icon: Bed, label: 'Admissions', path: '/admissions' },
	{ icon: Calendar, label: 'Clinic', path: '/clinic-sessions' },
	{ icon: Bell, label: 'Notifications', path: '/notifications' },
];

export const adminMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/admin' },
	// { icon: BarChart3, label: 'Analytics', path: '/admin/analytics' },
];

export const academicManagerMenuItems: MenuItem[] = [
	{ icon: BookOpen, label: 'Academics', path: '/academic-manager' },
];

export const receptionMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/reception' },
	{ icon: Users, label: 'Patient Queue', path: '/reception' },
	{ icon: Calendar, label: 'Appointments', path: '/clinic-sessions' },
];

export const nurseMenuItems: MenuItem[] = [
	{ icon: Stethoscope, label: 'Nurse Station', path: '/nurse-station' },
	{ icon: User, label: 'Profile', path: '/nurse-profile' },
];

export const nurseSuperintendentMenuItems: MenuItem[] = [
	{ icon: Stethoscope, label: 'Stations', path: '/nurse-superintendent' },
	{ icon: User, label: 'Profile', path: '/nurse-profile' },
];

export const nutritionistMenuItems: MenuItem[] = [
	{ icon: ChefHat, label: 'Nutritionist Portal', path: '/nutritionist' },
];

export const labTechnicianMenuItems: MenuItem[] = [
	{ icon: FlaskConical, label: 'Lab Dashboard', path: '/labs' },
];

export const billingMenuItems: MenuItem[] = [
	{ icon: CreditCard, label: 'Cashier', path: '/billing/cashier' },
];

export const accountsMenuItems: MenuItem[] = [
	{ icon: Landmark, label: 'Accounts', path: '/billing/accounts' },
	{ icon: CreditCard, label: 'Billing Users', path: '/billing/cashier' },
];

export const pharmacyMenuItems: MenuItem[] = [
	{ icon: Pill, label: 'Pharmacy Dashboard', path: '/pharmacy' },
];

export const otManagerMenuItems: MenuItem[] = [
	{ icon: Cpu, label: 'OT Dashboard', path: '/ot-manager' },
];

export const mrdMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/mrd/dashboard' },
	{ icon: BarChart3, label: 'Census', path: '/mrd/census' },
	{ icon: Archive, label: 'Records', path: '/mrd/records' },
	{ icon: Search, label: 'Patients', path: '/mrd/patients' },
	{ icon: Download, label: 'Exports', path: '/mrd/exports' },
];

export function getMenuItems(role: string): MenuItem[] {
	switch (role) {
		case 'PATIENT': return patientMenuItems;
		case 'STUDENT': return studentMenuItems;
		case 'FACULTY': return facultyMenuItems;
		case 'ADMIN': return adminMenuItems;
		case 'ACADEMIC_MANAGER': return academicManagerMenuItems;
		case 'RECEPTION': return receptionMenuItems;
		case 'NURSE': return nurseMenuItems;
		case 'NURSE_SUPERINTENDENT': return nurseSuperintendentMenuItems;
		case 'NUTRITIONIST': return nutritionistMenuItems;
		case 'LAB_TECHNICIAN': return labTechnicianMenuItems;
		case 'BILLING': return billingMenuItems;
		case 'ACCOUNTS': return accountsMenuItems;
		case 'PHARMACY': return pharmacyMenuItems;
		case 'OT_MANAGER': return otManagerMenuItems;
		case 'MRD': return mrdMenuItems;
		default: return patientMenuItems;
	}
}
