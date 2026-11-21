import { useEffect, useState } from "react";

export default function App() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d: { status: string }) => setStatus(d.status))
      .catch(() => setStatus("backend not reachable"));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: 24 }}>
      <h1>Explainable Payment Holds</h1>
      <p>Backend health: {status}</p>
      <footer>All data is synthetic. PayPal is sandbox only.</footer>
    </main>
  );
}
