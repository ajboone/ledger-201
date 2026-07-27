import { useEffect, useState, type FormEvent } from "react";

import "./App.css";


interface Vendor {
  id: number;
  name: string;
  created_at: string;
}


interface ApiErrorResponse {
  detail?: string;
}


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";


function App() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [vendorName, setVendorName] = useState("");

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(
    null,
  );

  useEffect(() => {
    async function loadVendors() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/vendors`);

        if (!response.ok) {
          throw new Error(
            `Vendor request failed with status ${response.status}.`,
          );
        }

        const vendorData = (await response.json()) as Vendor[];

        setVendors(vendorData);
      } catch (error) {
        if (error instanceof Error) {
          setErrorMessage(error.message);
        } else {
          setErrorMessage("An unknown error occurred.");
        }
      } finally {
        setIsLoading(false);
      }
    }

    void loadVendors();
  }, []);

  async function handleCreateVendor(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setFormError(null);
    setSuccessMessage(null);

    const normalizedName = vendorName.trim();

    if (!normalizedName) {
      setFormError("Enter a vendor name.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/vendors`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: normalizedName,
        }),
      });

      if (!response.ok) {
        const errorData =
          (await response.json()) as ApiErrorResponse;

        throw new Error(
          errorData.detail ??
            `Vendor request failed with status ${response.status}.`,
        );
      }

      const createdVendor = (await response.json()) as Vendor;

      setVendors((currentVendors) =>
        [...currentVendors, createdVendor].sort((first, second) =>
          first.name.localeCompare(second.name),
        ),
      );

      setVendorName("");
      setSuccessMessage(`${createdVendor.name} was added.`);
    } catch (error) {
      if (error instanceof Error) {
        setFormError(error.message);
      } else {
        setFormError("An unknown error occurred.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="app">
      <header>
        <p className="eyebrow">Restaurant operations platform</p>
        <h1>Ledger 201</h1>
        <p className="description">
          Vendor data loaded from the FastAPI backend.
        </p>
      </header>

      <section className="vendor-section">
        <h2>Vendors</h2>

        <form
          className="vendor-form"
          onSubmit={handleCreateVendor}
        >
          <label htmlFor="vendor-name">Vendor name</label>

          <div className="vendor-form-controls">
            <input
              id="vendor-name"
              type="text"
              value={vendorName}
              onChange={(event) => setVendorName(event.target.value)}
              placeholder="Pacific Seafood"
              maxLength={100}
              required
            />

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Adding..." : "Add vendor"}
            </button>
          </div>

          {formError && (
            <p className="form-message error-message" role="alert">
              {formError}
            </p>
          )}

          {successMessage && (
            <p className="form-message success-message">
              {successMessage}
            </p>
          )}
        </form>

        {isLoading && <p>Loading vendors...</p>}

        {errorMessage && (
          <p className="error-message">
            Unable to load vendors: {errorMessage}
          </p>
        )}

        {!isLoading && !errorMessage && vendors.length === 0 && (
          <p>No vendors have been created yet.</p>
        )}

        {!isLoading && !errorMessage && vendors.length > 0 && (
          <ul className="vendor-list">
            {vendors.map((vendor) => (
              <li key={vendor.id}>
                <strong>{vendor.name}</strong>
                <span>Vendor ID: {vendor.id}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}


export default App;