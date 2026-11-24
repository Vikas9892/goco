import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import { AuctionDetail } from "./pages/AuctionDetail";
import { AuctionList } from "./pages/AuctionList";
import { CreateRfq } from "./pages/CreateRfq";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="brand"><svg className="brand-mark" viewBox="0 0 32 32" aria-hidden>
            <rect x="7" y="8" width="4.5" height="16" rx="1.5" fill="#fff" />
            <rect x="13.75" y="12.5" width="4.5" height="11.5" rx="1.5" fill="#fff" fillOpacity=".85" />
            <rect x="20.5" y="17" width="4.5" height="7" rx="1.5" fill="#fff" fillOpacity=".7" />
          </svg>RFQ Auctions</Link>
          <nav>
            <NavLink to="/" end>Auctions</NavLink>
            <NavLink to="/new">New RFQ</NavLink>
          </nav>
        </div>
      </header>
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
