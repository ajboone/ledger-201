import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { createVendor, getVendors } from "../api/vendors";
import type { Vendor as VendorData } from "../types/vendor";
import "./Vendor.css";

const Vendor = () => {
  const [vendors, setVendors] = useState<VendorData[]>([]);
  const [vendorName, setVendorName] = useState("");

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadVendors() {
      try {
        const vendorData = await getVendors();

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

  async function handleCreateVendor(event: FormEvent<HTMLFormElement>) {
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
      const createdVendor = await createVendor(normalizedName);

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
    <div className="vendor">
      <header>
        <p className="eyebrow">Restaurant operations platform</p>
        <h1>Ledger 201</h1>
        <p className="description">
          Vendor data loaded from the FastAPI backend.
        </p>
      </header>

      <section className="vendor-section">
        <h2>Vendors</h2>

        <form className="vendor-form" onSubmit={handleCreateVendor}>
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
            <p className="form-message success-message">{successMessage}</p>
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
    </div>
  );
};

export default Vendor;
