import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { AuctionDetail } from "./pages/AuctionDetail";
import { AuctionList } from "./pages/AuctionList";
import { CreateRfq } from "./pages/CreateRfq";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <nav className="topbar"><Link to="/" className="brand">RFQ<span>·</span>Auctions</Link></nav>
      <main>
        <Routes>
          <Route path="/" element={<AuctionList />} />
          <Route path="/new" element={<CreateRfq />} />
          <Route path="/rfqs/:id" element={<AuctionDetail />} />
        </Routes>
      </main>
    </BrowserRouter>
  </StrictMode>,
);
