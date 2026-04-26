import client from './client';

export interface OTTheater {
  id: string;
  ot_id: string;
  name: string | null;
  location: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface OTBooking {
  id: string;
  theater_id: string;
  ot_id: string | null;
  ot_location: string | null;
  patient_id: string;
  patient_name: string | null;
  patient_display_id: string | null;
  student_id: string | null;
  date: string;
  from_date: string;
  to_date: string;
  start_time: string;
  end_time: string;
  procedure: string;
  doctor_name: string;
  notes: string | null;
  status: 'SCHEDULED' | 'CONFIRMED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  approved_by: string | null;
  created_at: string | null;
}

export interface OTSchedule {
  week_dates: string[];
  theaters: OTTheater[];
  bookings: OTBooking[];
}

export const otApi = {
  // Admin
  async listTheaters(): Promise<OTTheater[]> {
    return (await client.get('/ot/admin/theaters')).data;
  },
  async createTheater(data: { ot_id: string; name?: string; location?: string; description?: string }): Promise<OTTheater> {
    return (await client.post('/ot/admin/theaters', data)).data;
  },
  async updateTheater(id: string, data: Partial<OTTheater>): Promise<OTTheater> {
    return (await client.put(`/ot/admin/theaters/${id}`, data)).data;
  },
  async deleteTheater(id: string): Promise<void> {
    await client.delete(`/ot/admin/theaters/${id}`);
  },
  async updateBookingStatus(bookingId: string, status: string, approvedBy?: string): Promise<OTBooking> {
    return (await client.put(`/ot/admin/bookings/${bookingId}/status`, { status, approved_by: approvedBy })).data;
  },

  // Shared
  async getActiveTheaters(): Promise<OTTheater[]> {
    return (await client.get('/ot/theaters')).data;
  },
  async getSchedule(anchorDate?: string): Promise<OTSchedule> {
    const params = anchorDate ? { anchor_date: anchorDate } : {};
    return (await client.get('/ot/schedule', { params })).data;
  },

  // Student / Faculty
  async createBooking(data: {
    theater_id: string;
    patient_id: string;
    from_date: string;
    to_date: string;
    start_time: string;
    end_time: string;
    procedure: string;
    doctor_name: string;
    notes?: string;
  }): Promise<OTBooking> {
    return (await client.post('/ot/bookings', data)).data;
  },
  async getMyBookings(): Promise<OTBooking[]> {
    return (await client.get('/ot/bookings/mine')).data;
  },

  // OT Manager
  async getManagerProfile(): Promise<{ id: string; manager_id: string; name: string; phone: string | null; email: string | null; username: string }> {
    return (await client.get('/ot/manager/me')).data;
  },
  async managerGetBookings(date?: string, status?: string): Promise<OTBooking[]> {
    const params: Record<string, string> = {};
    if (date) params.date = date;
    if (status) params.status = status;
    return (await client.get('/ot/manager/bookings', { params })).data;
  },
  async approveBooking(bookingId: string): Promise<OTBooking> {
    return (await client.put(`/ot/manager/bookings/${bookingId}/approve`)).data;
  },
  async rejectBooking(bookingId: string): Promise<{ message: string }> {
    return (await client.put(`/ot/manager/bookings/${bookingId}/reject`)).data;
  },
  async managerUpdateBookingStatus(bookingId: string, status: string, approvedBy?: string): Promise<OTBooking> {
    return (await client.put(`/ot/manager/bookings/${bookingId}/status`, { status, approved_by: approvedBy })).data;
  },
};
