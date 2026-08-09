import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import App from "./App";
import SubmitPage from "./pages/SubmitPage";
import AnalysisPage from "./pages/AnalysisPage";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<SubmitPage />} />
          <Route path="analysis/:id" element={<AnalysisPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
