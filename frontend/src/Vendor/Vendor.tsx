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
    let active = true;

    async function loadVendors() {
      try {
        const vendorData = await getVendors();
        if (active) setVendors(vendorData);
      } catch (error) {
        if (active) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : "Unable to load vendors. Please try again.",
          );
        }
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void loadVendors();
    return () => {
      active = false;
    };
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
        <p className="description">Manage restaurant vendors.</p>
      </header>

      <section className="vendor-section">
        <div className="vendor-section-heading">
          <div>
            <p className="vendor-eyebrow">Supplier directory</p>
            <h2>Vendors</h2>
          </div>
          {!isLoading && !errorMessage && (
            <span className="vendor-count">
              {vendors.length} {vendors.length === 1 ? "vendor" : "vendors"}
            </span>
          )}
        </div>

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

        {isLoading && (
          <p className="vendor-state" role="status">
            Loading vendors...
          </p>
        )}

        {errorMessage && (
          <p className="vendor-state vendor-error" role="alert">
            Unable to load vendors: {errorMessage}
          </p>
        )}

        {!isLoading && !errorMessage && vendors.length === 0 && (
          <p className="vendor-state">
            No vendors yet. Add your first restaurant vendor above.
          </p>
        )}

        {!isLoading && !errorMessage && vendors.length > 0 && (
          <ul className="vendor-list">
            {vendors.map((vendor) => (
              <li className="vendor-card" key={vendor.id}>
                <span className="vendor-card-mark" aria-hidden="true">
                  {vendor.name.trim().charAt(0).toUpperCase()}
                </span>
                <div className="vendor-card-details">
                  <strong>{vendor.name}</strong>
                  <span>Restaurant vendor</span>
                </div>
                <time dateTime={vendor.created_at}>
                  Added{" "}
                  {new Date(vendor.created_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </time>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
};

export default Vendor;
