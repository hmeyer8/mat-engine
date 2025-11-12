"use client";
import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
const NdviMap = dynamic(() => import("../components/NdviMap"), { ssr: false });

type NdviItem = { file: string; tif?: string; color?: string; hot?: string; rgb?: string; bounds?: [number, number, number, number]; date?: string; mean?: number; tile?: string };

function prettyLabel(file: string) {
  // Expected: ndvi_YYYY-MM-DD_TILE.png
  const base = file.replace(/\.png$/i, "");
  const parts = base.split("_");
  if (parts.length >= 3) return `${parts[1]} • ${parts.slice(2).join("_")}`;
  return file;
}

export default function Home() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL;
  const [status, setStatus] = useState("Checking API…");
  const [items, setItems] = useState<NdviItem[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [overlayOpacity, setOverlayOpacity] = useState<number>(0.6);
  const [overlayMode, setOverlayMode] = useState<"hot" | "color">("hot");
  // ZIP-driven ingestion
  const [zip, setZip] = useState<string>("");
  const [jobId, setJobId] = useState<string>("");
  const [jobPhase, setJobPhase] = useState<"idle"|"queued"|"processing"|"done"|"failed">("idle");
  const [jobBounds, setJobBounds] = useState<[number, number, number, number] | null>(null);
  const [polling, setPolling] = useState<boolean>(false);
  // Onboarding/user info
  const [userName, setUserName] = useState<string>("");
  const [userEmail, setUserEmail] = useState<string>("");
  const haveUserInfo = userName.trim().length > 1 && /@/.test(userEmail);
  // Fields (derived from processed NDVI)
  type Field = { id: string; bounds: [number, number, number, number]; count: number; minDate?: string; maxDate?: string };
  const [fields, setFields] = useState<Field[]>([]);
  const [selectedFieldId, setSelectedFieldId] = useState<string>("");
  const selectedField = fields.find(f => f.id === selectedFieldId) || null;

  async function fetchAll() {
    try {
      setLoading(true);
      setError("");
      // Ping
      const pingRes = await fetch(`${apiBase}/api/ping`);
      if (!pingRes.ok) throw new Error(`Ping HTTP ${pingRes.status}`);
      const data = await pingRes.json();
      setStatus(data?.message ?? "OK");
      // Fields (only those with NDVI processed)
      const fieldsRes = await fetch(`${apiBase}/api/fields/list`);
      if (fieldsRes.ok) {
        const fl: Field[] = await fieldsRes.json();
        setFields(fl);
      }
      // NDVI list
      const listRes = await fetch(`${apiBase}/api/ndvi/list`);
      if (!listRes.ok) throw new Error(`List HTTP ${listRes.status}`);
      const list: NdviItem[] = await listRes.json();
      setItems(list);
      if (list.length > 0) setSelected(list[0].file);
    } catch (e: any) {
      console.error(e);
      setError(e?.message || "Failed to reach API");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]);

  const imageUrl = useMemo(() => {
    if (!selected) return "";
    const url = new URL(`${apiBase}/api/ndvi/image`);
    url.searchParams.set("file", selected);
    return url.toString();
  }, [apiBase, selected]);

  const colorUrl = useMemo(() => {
    const item = items.find((i) => i.file === selected);
    const color = item?.color;
    if (!color) return "";
    const url = new URL(`${apiBase}/api/ndvi/image`);
    url.searchParams.set("file", color);
    return url.toString();
  }, [apiBase, items, selected]);

  const hotUrl = useMemo(() => {
    const item = items.find((i) => i.file === selected);
    const hot = item?.hot;
    if (!hot) return "";
    const url = new URL(`${apiBase}/api/ndvi/image`);
    url.searchParams.set("file", hot);
    return url.toString();
  }, [apiBase, items, selected]);

  const rgbUrl = useMemo(() => {
    const item = items.find((i) => i.file === selected);
    const rgb = item?.rgb;
    if (!rgb) return "";
    const url = new URL(`${apiBase}/api/ndvi/image`);
    url.searchParams.set("file", rgb);
    return url.toString();
  }, [apiBase, items, selected]);

  const selectedItem = useMemo(() => items.find((i) => i.file === selected), [items, selected]);
  const activeOverlayUrl = useMemo(() => {
    if (overlayMode === "hot") return hotUrl || colorUrl;
    return colorUrl || hotUrl;
  }, [overlayMode, hotUrl, colorUrl]);
  const [timeline, setTimeline] = useState<NdviItem[]>([]);
  const [tIndex, setTIndex] = useState<number>(0);
  const [tLoading, setTLoading] = useState<boolean>(false);

  // Compute a map view bounds for fields selection (union of all fields)
  const fieldsViewBounds = useMemo<[number, number, number, number]>(() => {
    if (fields.length === 0) return [40, -97.2, 41, -96.3]; // fallback (NE area)
    let s = Infinity, w = Infinity, n = -Infinity, e = -Infinity;
    fields.forEach(f => {
      s = Math.min(s, f.bounds[0]);
      w = Math.min(w, f.bounds[1]);
      n = Math.max(n, f.bounds[2]);
      e = Math.max(e, f.bounds[3]);
    });
    return [s, w, n, e];
  }, [fields]);

  async function loadTimelineForSelected() {
    if (!selectedItem?.bounds) return;
    setTLoading(true);
    try {
      const [south, west, north, east] = selectedItem.bounds;
      const url = new URL(`${apiBase}/api/ndvi/search`);
      url.searchParams.set("south", String(south));
      url.searchParams.set("west", String(west));
      url.searchParams.set("north", String(north));
      url.searchParams.set("east", String(east));
      url.searchParams.set("limit", "200");
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(`Timeline HTTP ${res.status}`);
      const list: NdviItem[] = await res.json();
      setTimeline(list);
      if (list.length > 0) {
        setTIndex(list.length - 1); // start at latest
        setSelected(list[list.length - 1].file);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setTLoading(false);
    }
  }

  // When a field is chosen, fetch 2025 season analytics and populate items/timeline
  async function selectFieldAndLoad(field: Field) {
    setSelectedFieldId(field.id);
    setLoading(true);
    setError("");
    try {
      const [south, west, north, east] = field.bounds;
      const url = new URL(`${apiBase}/api/ndvi/search`);
      url.searchParams.set("south", String(south));
      url.searchParams.set("west", String(west));
      url.searchParams.set("north", String(north));
      url.searchParams.set("east", String(east));
      url.searchParams.set("start", "2025-03-01"); // 2025 growing season (approx)
      url.searchParams.set("end", "2025-10-31");
      url.searchParams.set("limit", "300");
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(`Search HTTP ${res.status}`);
      const list: NdviItem[] = await res.json();
      setItems(list);
      setTimeline(list);
      if (list.length > 0) {
        setTIndex(list.length - 1);
        setSelected(list[list.length - 1].file);
      } else {
        setSelected("");
        setTIndex(0);
      }
    } catch (e: any) {
      console.error(e);
      setError(e?.message || "Failed to load analytics for field");
    } finally {
      setLoading(false);
    }
  }

  // Submit ZIP to create a background ingest job and poll until results appear
  async function submitZipIngest() {
    if (!zip || zip.trim().length < 3) return;
    setError("");
    setJobPhase("queued");
    setPolling(true);
    try {
      const res = await fetch(`${apiBase}/api/ingest/zip?zip=${encodeURIComponent(zip.trim())}`);
      if (!res.ok) throw new Error(`Ingest HTTP ${res.status}`);
      const payload = await res.json();
      const jb = payload.bounds as [number, number, number, number];
      setJobId(payload.jobId);
      setJobBounds(jb);
      // Immediately try to load any existing scenes in that area
      await pollForResults(jb, payload.start, payload.end, payload.jobId);
    } catch (e: any) {
      console.error(e);
      setError(e?.message || "Failed to start ingest job");
      setJobPhase("failed");
      setPolling(false);
    }
  }

  // Poll API status and NDVI search for the job bounds until we detect new results
  async function pollForResults(bounds: [number, number, number, number], start?: string, end?: string, jbId?: string) {
    const [south, west, north, east] = bounds;
    const seen = new Set(items.map(i => i.file));
    const startedAt = Date.now();
    const timeoutMs = 8 * 60 * 1000; // 8 minutes
    const intervalMs = 8000; // 8s cadence

    async function tick() {
      try {
        // Check job status if we have a jobId
        if (jbId) {
          const js = await fetch(`${apiBase}/api/ingest/status?jobId=${encodeURIComponent(jbId)}`).then(r => r.json());
          if (js.status === 'failed') {
            setJobPhase('failed');
            setPolling(false);
            return true;
          }
          if (js.status === 'pending') setJobPhase('processing');
          if (js.status === 'done') setJobPhase('done');
        }
        // Query for results in the bounds
        const url = new URL(`${apiBase}/api/ndvi/search`);
        url.searchParams.set("south", String(south));
        url.searchParams.set("west", String(west));
        url.searchParams.set("north", String(north));
        url.searchParams.set("east", String(east));
        if (start) url.searchParams.set("start", String(start));
        if (end) url.searchParams.set("end", String(end));
        url.searchParams.set("limit", "300");
        const res = await fetch(url.toString());
        if (res.ok) {
          const list: NdviItem[] = await res.json();
          const newOnes = list.filter(i => !seen.has(i.file));
          if (list.length > 0 && newOnes.length > 0) {
            // Merge and present latest
            setItems(list);
            setTimeline(list);
            setSelected(list[list.length - 1].file);
            setTIndex(Math.max(0, list.length - 1));
            setJobPhase('done');
            setPolling(false);
            // Refresh fields so newly-covered land appears
            try {
              const fieldsRes = await fetch(`${apiBase}/api/fields/list`);
              if (fieldsRes.ok) setFields(await fieldsRes.json());
            } catch {}
            return true;
          }
          // If job marked done but we didn't detect new files, ease out of processing
          if (list.length > 0 && jobPhase === 'done') {
            setItems(list);
            setTimeline(list);
            setSelected(list[list.length - 1].file);
            setTIndex(Math.max(0, list.length - 1));
            setPolling(false);
            try {
              const fieldsRes = await fetch(`${apiBase}/api/fields/list`);
              if (fieldsRes.ok) setFields(await fieldsRes.json());
            } catch {}
            return true;
          }
        }
        if (Date.now() - startedAt > timeoutMs) {
          setJobPhase('failed');
          setPolling(false);
          return true;
        }
        return false;
      } catch (err) {
        console.error(err);
        return false;
      }
    }

    // Run immediate tick, then interval until done
    if (await tick()) return;
    const handle = setInterval(async () => {
      const done = await tick();
      if (done) clearInterval(handle);
    }, intervalMs);
  }

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 py-2.5 px-3 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <h1 className="text-sm sm:text-base font-semibold tracking-tight text-gray-800">MAT Engine · Field Imagery</h1>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-gray-500 hidden sm:inline-flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
              {status}
            </span>
            <button
              onClick={fetchAll}
              className="inline-flex items-center gap-1 rounded border border-gray-300 bg-white px-2 py-1 text-[11px] shadow-sm hover:bg-gray-50"
              aria-label="Refresh data"
            >
              Refresh
            </button>
          </div>
        </div>
      </header>

      <section className="px-3 sm:px-4 py-4">
        {/* About / Purpose */}
        <div className="max-w-6xl mx-auto mb-4">
          <div className="rounded-lg border border-gray-200 bg-white p-3 sm:p-4 shadow-sm">
            <div className="text-sm sm:text-base font-medium text-gray-800">Why this exists</div>
            <p className="mt-1.5 text-[13px] sm:text-sm text-gray-700 leading-relaxed">
              MAT Engine helps growers and agronomists monitor crop vigor from space. We ingest Sentinel‑2 imagery,
              compute NDVI, and overlay hotspots on true‑color basemaps so anyone can spot stress early, compare
              fields over time, and make informed decisions—no GIS expertise required.
            </p>
            <ul className="mt-2 text-[12px] sm:text-[13px] text-gray-600 grid gap-1 sm:grid-cols-2 list-disc list-inside">
              <li>True‑color base + NDVI hotspots overlay</li>
              <li>Browse scenes and scrub a simple timeline</li>
              <li>Runs locally with Docker; data stays on your machine</li>
              <li>Built on Microsoft Planetary Computer and open data</li>
            </ul>
          </div>
        </div>
        {loading && (
          <div className="animate-pulse space-y-3">
            <div className="h-5 w-64 bg-gray-200 rounded" />
            <div className="h-72 w-full max-w-3xl bg-gray-100 rounded" />
          </div>
        )}

        {!!error && (
          <div className="bg-red-50 text-red-800 border border-red-200 rounded-md px-4 py-3 mb-4">
            {error}
          </div>
        )}

        {!loading && items.length === 0 && !error && (
          <div className="bg-blue-50 border border-blue-200 text-blue-900 p-4 rounded-md">
            <p className="font-medium">No NDVI previews found.</p>
            <p className="mt-1 text-sm">Run the ingestor to fetch Sentinel‑2 and compute NDVI:</p>
            <pre className="mt-2 text-xs bg-slate-900 text-slate-100 p-3 rounded">docker compose run --rm ingestor</pre>
          </div>
        )}

        {(items.length > 0 || fields.length > 0) && (
          <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Left: Controls & List */}
            <aside className="lg:col-span-4 space-y-4">
              {/* ZIP Ingest card */}
              <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                <div className="px-3 py-2.5 border-b border-gray-100">
                  <div className="font-semibold text-sm">Get imagery for your ZIP</div>
                  <div className="text-[11px] text-gray-500">We will fetch the latest scenes and compute NDVI</div>
                </div>
                <div className="p-3 space-y-2 text-sm">
                  <div className="flex gap-2">
                    <input value={zip} onChange={(e)=>setZip(e.target.value)} placeholder="Enter ZIP (e.g., 68516)" className="flex-1 rounded-md border border-gray-200 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500" />
                    <button onClick={submitZipIngest} disabled={!zip || polling} className="rounded-md bg-blue-600 text-white px-3 py-2 text-sm disabled:opacity-50">{polling? 'Processing…':'Run'}</button>
                  </div>
                  {jobPhase !== 'idle' && (
                    <div className="text-[12px] text-gray-600 flex items-center gap-2">
                      <span className={`inline-block h-2 w-2 rounded-full ${jobPhase==='done'?'bg-emerald-500': jobPhase==='failed'?'bg-red-500':'bg-amber-500'} `}/>
                      <span>
                        {jobPhase==='queued' && 'Queued…'}
                        {jobPhase==='processing' && 'Processing imagery… this can take a minute'}
                        {jobPhase==='done' && 'Done! New scenes are available below.'}
                        {jobPhase==='failed' && 'Something went wrong. Please retry.'}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              {/* User info card */}
              <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                <div className="px-3 py-2.5 border-b border-gray-100">
                  <div className="font-semibold text-sm">Your info</div>
                  <div className="text-[11px] text-gray-500">Tell us who you are</div>
                </div>
                <div className="p-3 space-y-2 text-sm">
                  <input value={userName} onChange={(e)=>setUserName(e.target.value)} placeholder="Full name" className="w-full rounded-md border border-gray-200 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500" />
                  <input value={userEmail} onChange={(e)=>setUserEmail(e.target.value)} placeholder="Email" className="w-full rounded-md border border-gray-200 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500" />
                  {!haveUserInfo && <div className="text-[11px] text-amber-700">Enter name and a valid email to continue.</div>}
                </div>
              </div>

              {/* Field selection helper */}
              <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                <div className="px-3 py-2.5 border-b border-gray-100">
                  <div className="font-semibold text-sm">Select your land</div>
                  <div className="text-[11px] text-gray-500">Only fields with NDVI appear</div>
                </div>
                <div className="p-3 text-[12px] text-gray-600">
                  {fields.length === 0 ? (
                    <div>No fields yet. Ingest imagery to populate fields.</div>
                  ) : (
                    <div className="space-y-2">
                      <div>Click a field on the map to load 2025 analytics.</div>
                      <div className="grid grid-cols-2 gap-2">
                        {fields.slice(0,6).map(f => (
                          <button key={f.id} onClick={()=> selectFieldAndLoad(f)} className={`rounded border px-2 py-1 text-left ${selectedFieldId===f.id?'border-blue-500 ring-2 ring-blue-200':'border-gray-200 hover:border-gray-300'}`}>
                            <div className="text-[12px] font-medium">Field {f.id.slice(0,6)}</div>
                            <div className="text-[11px] text-gray-500">scenes: {f.count}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              {/* Selector Card */}
              <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                <div className="px-3 py-2.5 border-b border-gray-100">
                  <div className="font-semibold text-sm">Select scene</div>
                  <div className="text-[11px] text-gray-500">Choose NDVI preview</div>
                </div>
                <div className="p-3 space-y-3">
                  <select
                    id="ndvi-select"
                    value={selected}
                    onChange={(e) => setSelected(e.target.value)}
                    className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {items.map((it) => (
                      <option key={it.file} value={it.file}>
                        {prettyLabel(it.file)}
                      </option>
                    ))}
                  </select>
                  {selectedItem && (
                    <div className="text-[11px] text-gray-600 flex flex-wrap gap-2">
                      {selectedItem.date && (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5">{selectedItem.date}</span>
                      )}
                      {selectedItem.tile && (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5">{(selectedItem as any).tile}</span>
                      )}
                      {typeof (selectedItem as any)?.mean === "number" && (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5">mean {(selectedItem as any).mean.toFixed(3)}</span>
                      )}
                    </div>
                  )}

                  {/* Thumbnails */}
                  <div className="pt-2">
                    <div className="text-[11px] text-gray-500 mb-1">Quick picks</div>
                    <div className="grid grid-cols-3 gap-2">
                      {items.slice(0, 9).map((it) => {
                        const img = it.color || it.file;
                        const url = new URL(`${apiBase}/api/ndvi/image`);
                        url.searchParams.set("file", img);
                        const active = selected === it.file;
                        return (
                          <button
                            key={it.file}
                            onClick={() => setSelected(it.file)}
                            className={`group relative rounded-md overflow-hidden border ${active ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-200 hover:border-gray-300'}`}
                            title={prettyLabel(it.file)}
                          >
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={url.toString()} alt={it.file} className="h-16 w-full object-cover" />
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>

              {/* Overlay Controls */}
              <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                <div className="px-3 py-2.5 border-b border-gray-100">
                  <div className="font-semibold text-sm">Overlay controls</div>
                  <div className="text-[11px] text-gray-500">Adjust visualization</div>
                </div>
                <div className="p-3 space-y-3 text-sm">
                  <div className="flex items-center gap-4 text-xs">
                    <label className="inline-flex items-center gap-1">
                      <input type="radio" name="ovmode" checked={overlayMode==='hot'} onChange={() => setOverlayMode('hot')} />
                      Hotspots
                    </label>
                    <label className="inline-flex items-center gap-1">
                      <input type="radio" name="ovmode" checked={overlayMode==='color'} onChange={() => setOverlayMode('color')} />
                      Color overlay
                    </label>
                  </div>
                  <label className="block">Opacity: {(overlayOpacity * 100).toFixed(0)}%</label>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={overlayOpacity}
                    onChange={(e) => setOverlayOpacity(Number(e.target.value))}
                    className="w-full"
                  />
                  <div className="text-xs text-gray-500">Dark red = higher NDVI • Light red = lower NDVI</div>
                </div>
              </div>

              {/* Legend */}
              <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden p-4">
                <div className="font-semibold mb-2">NDVI legend</div>
                <div className="h-3 rounded w-full" style={{
                  background: "linear-gradient(to right, #ffc0c0, #800000)"
                }} />
                <div className="mt-2 flex justify-between text-xs text-gray-600">
                  <span>lower</span>
                  <span>higher</span>
                </div>
              </div>
            </aside>

            {/* Right: Map & Preview */}
            <div className="lg:col-span-8 space-y-4">
              {/* Field selection map */}
              {/* Show field selection only after a ZIP has been submitted to keep focus */}
              {jobBounds && fields.length > 0 && !selectedField && (
                <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                  <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-100">
                    <div className="font-semibold">Pick a field to analyze</div>
                    {!haveUserInfo && <div className="text-[11px] text-amber-700">Enter name and email to proceed</div>}
                  </div>
                  <div className={`p-3 ${!haveUserInfo ? 'opacity-50 pointer-events-none' : ''}`}>
                    <NdviMap
                      bounds={fieldsViewBounds}
                      height={360}
                      fields={fields as any}
                      selectedFieldId={selectedFieldId}
                      onSelectField={(id)=>{ const f = fields.find(ff=>ff.id===id); if (f && haveUserInfo) selectFieldAndLoad(f); }}
                      maxBounds={jobBounds || undefined}
                    />
                  </div>
                </div>
              )}
              {/* Map overlay when bounds/color available */}
              {jobBounds && selectedItem?.bounds && (hotUrl || colorUrl) ? (
                <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                  <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-100">
                    <div className="font-semibold">Map overlay</div>
                    <div className="text-xs text-gray-500">Overlay opacity {(overlayOpacity * 100).toFixed(0)}%</div>
                  </div>
                  <div className="p-3">
                    <NdviMap
                      imageUrl={activeOverlayUrl as string}
                      baseImageUrl={rgbUrl || undefined}
                      bounds={selectedItem.bounds as [number, number, number, number]}
                      opacity={overlayOpacity}
                      height={360}
                      maxBounds={jobBounds || undefined}
                    />
                  </div>
                </div>
              ) : null}

              {/* Compact links */}
              <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-100">
                  <div className="font-semibold">Downloads</div>
                </div>
                <div className="p-3 text-sm text-blue-700 flex flex-wrap gap-4">
                  {rgbUrl && (
                    <a className="hover:underline" href={`${apiBase}/api/ndvi/image?file=${encodeURIComponent((selectedItem as any)?.rgb)}`} target="_blank" rel="noreferrer">Open RGB</a>
                  )}
                  {selected && (
                    <a className="hover:underline" href={`${apiBase}/api/ndvi/image?file=${encodeURIComponent(selected)}`} target="_blank" rel="noreferrer">Open NDVI PNG</a>
                  )}
                  {(selectedItem as any)?.color && (
                    <a className="hover:underline" href={`${apiBase}/api/ndvi/image?file=${encodeURIComponent((selectedItem as any)?.color)}`} target="_blank" rel="noreferrer">Open Color overlay</a>
                  )}
                  {(selectedItem as any)?.hot && (
                    <a className="hover:underline" href={`${apiBase}/api/ndvi/image?file=${encodeURIComponent((selectedItem as any)?.hot)}`} target="_blank" rel="noreferrer">Open Hotspots</a>
                  )}
                </div>
              </div>

              {/* Timeline */}
              <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                  <div className="font-semibold">Time series</div>
                  <button
                    onClick={loadTimelineForSelected}
                    className="text-sm text-blue-600 hover:underline disabled:opacity-50"
                    disabled={!selectedItem?.bounds || tLoading}
                  >
                    {tLoading ? "Loading…" : "Load timeline for this field"}
                  </button>
                </div>
                {timeline.length > 0 ? (
                  <div className="px-4 pb-4">
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>{timeline[0]?.date || ""}</span>
                      <span>{timeline[timeline.length - 1]?.date || ""}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={Math.max(0, timeline.length - 1)}
                      value={tIndex}
                      onChange={(e) => {
                        const idx = Number(e.target.value);
                        setTIndex(idx);
                        const item = timeline[idx];
                        if (item?.file) setSelected(item.file);
                      }}
                      className="w-full"
                    />
                    <div className="mt-2 text-sm">
                      <span className="font-medium">Date:</span> {timeline[tIndex]?.date || ""}
                      {typeof (timeline[tIndex] as any)?.mean === "number" && (
                        <span className="ml-3 text-gray-600">Mean NDVI: {(timeline[tIndex] as any).mean?.toFixed(3)}</span>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="px-4 pb-4 text-sm text-gray-500">No timeline loaded.</div>
                )}
              </div>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
