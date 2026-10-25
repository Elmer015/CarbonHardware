import { useEffect, useState } from "react";
import EstimateCarbon from "./pages/EstimateCarbon";
import StecResults from "./pages/StecResults";
import Comparison from "./pages/Comparison";

const routes = { "/": EstimateCarbon, "/estimate": EstimateCarbon, "/stec": StecResults, "/comparison": Comparison };
function navigate(path) { window.history.pushState({}, "", path); window.dispatchEvent(new PopStateEvent("popstate")); }

export default function App() {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => { const onPopState = () => setPath(window.location.pathname); window.addEventListener("popstate", onPopState); return () => window.removeEventListener("popstate", onPopState); }, []);
  const Page = routes[path] || EstimateCarbon;
  return <div className="app-shell"><aside className="sidebar">
    <a className="brand" href="/" onClick={(e) => { e.preventDefault(); navigate("/"); }}><span className="brand-mark">C</span><span><strong>Carbon</strong><small>HARDWARE</small></span></a>
    <div className="workspace-label">MODEL WORKSPACE</div><nav className="nav-list" aria-label="Main navigation">
      <NavItem href="/" active={path === "/" || path === "/estimate"} icon="⌁" label="Embodied carbon" />
      <NavItem href="/stec" active={path === "/stec"} icon="↗" label="STEC per processor" />
      <NavItem href="/comparison" active={path === "/comparison"} icon="⇄" label="Baseline vs STEC" />
    </nav>
    <div className="sidebar-note"><span className="status-dot" /> Experimental baseline<p>Prediction follows the five features required by the trained artifact.</p></div><div className="sidebar-footer">Research project · 2026</div>
  </aside><main className="main-content"><Page navigate={navigate} /></main></div>;
}
function NavItem({ href, active, icon, label }) { return <a className={`nav-item ${active ? "active" : ""}`} href={href} onClick={(e) => { e.preventDefault(); navigate(href); }}><span className="nav-icon">{icon}</span>{label}</a>; }