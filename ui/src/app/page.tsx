"use client";
import { useEffect, useState } from "react";

export default function Home() {
  const [status, setStatus] = useState("Loading...");

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/ping`)
      .then(res => res.text())
      .then(txt => setStatus(txt))
      .catch(err => setStatus("Error connecting to API"));
  }, []);

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>Meyer AgTech Dashboard</h1>
      <p>Backend status: {status}</p>
    </main>
  );
}
