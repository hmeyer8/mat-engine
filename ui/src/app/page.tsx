"use client";
import { useEffect, useState } from "react";

export default function Home() {
  const [status, setStatus] = useState("Loading...");

  useEffect(() => {
    const url = `${process.env.NEXT_PUBLIC_API_URL}/api/ping`;
    console.log("Calling API:", url);
    fetch(url)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setStatus(data?.message ?? "OK");
      })
      .catch((e) => {
        console.error("API error:", e);
        setStatus("Error connecting to API");
      });
  }, []);

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>Meyer AgTech Dashboard</h1>
      <p>Backend status: {status}</p>
    </main>
  );
}
