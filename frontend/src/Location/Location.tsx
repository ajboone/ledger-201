import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { createLocation, getLocations } from "../api/locations";
import type { Location as LocationData } from "../types/location";
import "./Location.css";

const Location = () => {
  const [locations, setLocations] = useState<LocationData[]>([]);
  const [name, setName] = useState("");
  const [squareLocationId, setSquareLocationId] = useState("");
  const [timezone, setTimezone] = useState("America/New_York");
  const [currency, setCurrency] = useState("USD");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadLocations() {
      try {
        const locationData = await getLocations();
        if (active) setLocations(locationData);
      } catch (error) {
        if (active) {
          setErrorMessage(error instanceof Error ? error.message : "An unknown error occurred.");
        }
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void loadLocations();
    return () => { active = false; };
  }, []);

  async function handleCreateLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);

    const normalizedName = name.trim();
    if (!normalizedName) {
      setFormError("Enter a location name.");
      return;
    }

    setIsSubmitting(true);
    try {
      const createdLocation = await createLocation({
        name: normalizedName,
        square_location_id: squareLocationId.trim() || null,
        timezone: timezone.trim(),
        currency: currency.trim(),
      });

      setLocations((currentLocations) =>
        [...currentLocations, createdLocation].sort((first, second) =>
          first.name.localeCompare(second.name),
        ),
      );
      setName("");
      setSquareLocationId("");
      setTimezone("America/New_York");
      setCurrency("USD");
      setSuccessMessage(`${createdLocation.name} was added.`);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "An unknown error occurred.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="location">
      <header>
        <p className="eyebrow">Restaurant operations platform</p>
        <h1>Ledger 201</h1>
        <p className="description">Manage your restaurant locations.</p>
      </header>

      <section className="location-section">
        <h2>Locations</h2>
        <form className="location-form" onSubmit={handleCreateLocation}>
          <label htmlFor="location-name">Location name</label>
          <input id="location-name" type="text" value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Downtown" maxLength={100} required />

          <label htmlFor="location-square-id">Square location ID (optional)</label>
          <input id="location-square-id" type="text" value={squareLocationId}
            onChange={(event) => setSquareLocationId(event.target.value)} maxLength={64} />

          <label htmlFor="location-timezone">Timezone</label>
          <input id="location-timezone" type="text" value={timezone}
            onChange={(event) => setTimezone(event.target.value)} maxLength={64} required />

          <label htmlFor="location-currency">Currency</label>
          <input id="location-currency" type="text" value={currency}
            onChange={(event) => setCurrency(event.target.value)}
            minLength={3} maxLength={3} required />

          <button type="submit" disabled={isSubmitting || isLoading}>
            {isSubmitting ? "Adding..." : "Add location"}
          </button>

          {formError && <p className="form-message error-message" role="alert">{formError}</p>}
          {successMessage && <p className="form-message success-message" role="status">{successMessage}</p>}
        </form>

        {isLoading && <p role="status">Loading locations...</p>}
        {errorMessage && <p className="error-message" role="alert">Unable to load locations: {errorMessage}</p>}
        {!isLoading && !errorMessage && locations.length === 0 && <p>No locations have been created yet.</p>}
        {!isLoading && locations.length > 0 && (
          <ul className="location-list">
            {locations.map((location) => (
              <li key={location.id}>
                <strong>{location.name}</strong>
                <span>Location ID: {location.id}</span>
                <span>Square location ID: {location.square_location_id ?? "Not set"}</span>
                <span>Timezone: {location.timezone}</span>
                <span>Currency: {location.currency}</span>
                <span>Status: {location.is_active ? "Active" : "Inactive"}</span>
                <span>Created: <time dateTime={location.created_at}>{new Date(location.created_at).toLocaleString()}</time></span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
};

export default Location;
