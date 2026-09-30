import { apiRequest } from "./client";
import type { Vendor } from "../types/vendor";

export function getVendors(): Promise<Vendor[]> {
  return apiRequest<Vendor[]>("/api/vendors", {}, "Vendor");
}

export function createVendor(name: string): Promise<Vendor> {
  return apiRequest<Vendor>(
    "/api/vendors",
    {
      method: "POST",
      body: JSON.stringify({ name }),
    },
    "Vendor",
  );
}
