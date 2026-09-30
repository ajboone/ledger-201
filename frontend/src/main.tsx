import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import App from "./App.tsx";
import "./index.css";
import Navbar from "./Navbar";
import Vendor from "./Vendor";
import Location from "./Location";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="vendor" element={<Vendor />} />
        <Route path="location" element={<Location />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
