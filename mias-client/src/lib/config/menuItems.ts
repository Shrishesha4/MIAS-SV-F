import {
	Home, User, FileText, Clipboard, Pill, Activity,
	TestTube, Wallet, Bell, GraduationCap,
	Users, CheckCircle, Bed, Calendar, Building, BarChart3
} from 'lucide-svelte';

export interface MenuItem {
	icon: any;
	label: string;
	path: string;
}

export const patientMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/dashboard' },
	{ icon: User, label: 'Profile', path: '/profile' },
	{ icon: FileText, label: 'Medical Records', path: '/records' },
	{ icon: Bed, label: 'Admissions', path: '/admissions' },
	{ icon: Pill, label: 'Prescriptions', path: '/prescriptions' },
	{ icon: Activity, label: 'Vitals', path: '/vitals' },
	{ icon: TestTube, label: 'Reports', path: '/reports' },
	{ icon: Calendar, label: 'Clinic', path: '/clinic-sessions' },
	{ icon: Wallet, label: 'Hospital Wallet', path: '/wallet/hospital' },
	{ icon: Wallet, label: 'Pharmacy Wallet', path: '/wallet/pharmacy' },
	{ icon: Bell, label: 'Notifications', path: '/notifications' },
];

export const studentMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/dashboard' },
	{ icon: User, label: 'Profile', path: '/profile' },
	{ icon: Users, label: 'Assigned Patients', path: '/patients' },
	{ icon: Clipboard, label: 'Case Records', path: '/case-records' },
	{ icon: Bed, label: 'Admissions', path: '/admissions' },
	{ icon: Calendar, label: 'Clinic Sessions', path: '/clinic-sessions' },
	{ icon: Bell, label: 'Notifications', path: '/notifications' },
];

export const facultyMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/dashboard' },
	{ icon: User, label: 'Profile', path: '/profile' },
	{ icon: CheckCircle, label: 'Approvals', path: '/approvals' },
	{ icon: GraduationCap, label: 'Students', path: '/students' },
	{ icon: Bed, label: 'Admissions', path: '/admissions' },
	{ icon: Calendar, label: 'Clinic', path: '/clinic-sessions' },
	{ icon: Bell, label: 'Notifications', path: '/notifications' },
];

export const adminMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/admin' },
	{ icon: Users, label: 'User Management', path: '/admin/users' },
	{ icon: Building, label: 'Departments', path: '/admin/departments' },
	{ icon: Calendar, label: 'Clinic', path: '/clinic-sessions' },
	{ icon: BarChart3, label: 'Analytics', path: '/admin/analytics' },
];

export const receptionMenuItems: MenuItem[] = [
	{ icon: Home, label: 'Dashboard', path: '/reception' },
	{ icon: Users, label: 'Patient Queue', path: '/reception' },
	{ icon: Calendar, label: 'Appointments', path: '/clinic-sessions' },
];

export function getMenuItems(role: string): MenuItem[] {
	switch (role) {
		case 'PATIENT': return patientMenuItems;
		case 'STUDENT': return studentMenuItems;
		case 'FACULTY': return facultyMenuItems;
		case 'ADMIN': return adminMenuItems;
		case 'RECEPTION': return receptionMenuItems;
		default: return patientMenuItems;
	}
}
