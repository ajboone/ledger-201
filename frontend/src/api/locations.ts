import { apiRequest } from "./client";
import type { Location, LocationCreate } from "../types/location";

export function getLocations(): Promise<Location[]> {
  return apiRequest<Location[]>("/api/locations", {}, "Location");
}

export function createLocation(location: LocationCreate): Promise<Location> {
  return apiRequest<Location>(
    "/api/locations",
    {
      method: "POST",
      body: JSON.stringify(location),
    },
    "Location",
  );
}
