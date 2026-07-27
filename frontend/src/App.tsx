import { useEffect, useState } from "react";

import "./App.css";


interface Vendor {
  id: number;
  name: string;
  created_at: string;
}


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";


function App() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadVendors() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/vendors`);

        if (!response.ok) {
          throw new Error(
            `Vendor request failed with status ${response.status}.`,
          );
        }

        const vendorData: Vendor[] = await response.json();

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
