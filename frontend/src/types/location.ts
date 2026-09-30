export interface Location {
  id: number;
  name: string;
  square_location_id: string | null;
  timezone: string;
  currency: string;
  is_active: boolean;
  created_at: string;
}

export interface LocationCreate {
  name: string;
  square_location_id?: string | null;
  timezone?: string;
  currency?: string;
}
