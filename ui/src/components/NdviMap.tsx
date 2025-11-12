"use client";
import { useEffect, useMemo, useRef } from "react";
import L, { type LatLngBoundsExpression, type Map as LeafletMap } from "leaflet";

export type NdviBounds = [number, number, number, number]; // [south, west, north, east]

export default function NdviMap({
  imageUrl,
  bounds,
  opacity = 0.6,
  baseImageUrl,
  height = 380,
  fields,
  selectedFieldId,
  onSelectField,
  maxBounds,
}: {
  imageUrl?: string; // overlay (hot/color)
  bounds: NdviBounds;
  opacity?: number;
  baseImageUrl?: string; // true-color underlay
  height?: number;
  fields?: Array<{ id: string; bounds: NdviBounds }>;
  selectedFieldId?: string;
  onSelectField?: (id: string) => void;
  maxBounds?: NdviBounds;
}) {
  const mapEl = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const fieldLayerRefs = useRef<Record<string, L.Rectangle>>({});

  const leafletBounds = useMemo<LatLngBoundsExpression>(() => [
    [bounds[0], bounds[1]],
    [bounds[2], bounds[3]],
  ], [bounds]);

  useEffect(() => {
    if (!mapEl.current) return;
    if (!mapRef.current) {
      // Init map
      const lat = (bounds[0] + bounds[2]) / 2;
      const lng = (bounds[1] + bounds[3]) / 2;
      const options: L.MapOptions = {};
      if (maxBounds) {
        options.maxBounds = [
          [maxBounds[0], maxBounds[1]],
          [maxBounds[2], maxBounds[3]],
        ];
        // Slight resistance to leaving the area
        // @ts-ignore - property exists at runtime
        options.maxBoundsViscosity = 1.0;
      }
      const map = L.map(mapEl.current, options).setView([lat, lng], 11);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);
      L.control.scale({ imperial: false }).addTo(map);
      mapRef.current = map;
    }
    const map = mapRef.current!;
    if (maxBounds) {
      const mb: LatLngBoundsExpression = [
        [maxBounds[0], maxBounds[1]],
        [maxBounds[2], maxBounds[3]],
      ];
      map.setMaxBounds(mb);
    }
    // Fit bounds
    map.fitBounds(leafletBounds);
    // Add optional base underlay first
    let baseLayer: L.ImageOverlay | null = null;
    if (baseImageUrl) {
      baseLayer = L.imageOverlay(baseImageUrl, leafletBounds, { opacity: 1.0 });
      baseLayer.addTo(map);
    }
    // Add overlay
    let overlay: L.ImageOverlay | null = null;
    if (imageUrl) {
      overlay = L.imageOverlay(imageUrl, leafletBounds, { opacity });
      overlay.addTo(map);
    }
    // Draw fields as rectangles (clickable)
    const addedRects: L.Rectangle[] = [];
    if (fields && fields.length > 0) {
      fields.forEach((f) => {
        const fb: LatLngBoundsExpression = [
          [f.bounds[0], f.bounds[1]],
          [f.bounds[2], f.bounds[3]],
        ];
        const active = selectedFieldId && f.id === selectedFieldId;
        const rect = L.rectangle(fb, {
          color: active ? '#2563eb' : '#10b981',
          weight: active ? 3 : 2,
          fill: true,
          fillOpacity: active ? 0.1 : 0.06,
        }).addTo(map);
        rect.on('click', () => onSelectField && onSelectField(f.id));
        addedRects.push(rect);
        fieldLayerRefs.current[f.id] = rect;
      });
    }
    return () => {
      if (baseLayer) baseLayer.remove();
      if (overlay) overlay.remove();
      addedRects.forEach(r => r.remove());
    };
  }, [imageUrl, baseImageUrl, leafletBounds, opacity, bounds, fields, selectedFieldId, onSelectField]);

  return <div ref={mapEl} style={{ width: "100%", height: `${height}px`, maxHeight: '70vh', borderRadius: 12, overflow: "hidden" }} />;
}
