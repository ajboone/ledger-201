import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import App from "./App.tsx";
import "./index.css";
import Navbar from "./Navbar";
import Vendor from "./Vendor";
import Location from "./Location";
import DailyReview from "./DailyReview/DailyReview";
import SquareReports from "./SquareReports/SquareReports";
import ConversationProvider from "./Chatbot/ConversationProvider";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <ConversationProvider>
        <Navbar />
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="vendor" element={<Vendor />} />
          <Route path="location" element={<Location />} />
          <Route path="daily-review" element={<DailyReview />} />
          <Route path="square-reports" element={<SquareReports />} />
        </Routes>
      </ConversationProvider>
    </BrowserRouter>
  </StrictMode>,
);
