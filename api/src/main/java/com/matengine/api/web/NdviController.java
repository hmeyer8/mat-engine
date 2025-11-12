package com.matengine.api.web;

import org.springframework.core.io.FileSystemResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.ArrayList;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;

@RestController
@RequestMapping("/api/ndvi")
public class NdviController {

    private static final Path BASE_DIR = Paths.get("/workspace/data/processed/sentinel-2");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @GetMapping("/list")
    public List<Map<String, Object>> listNdvi() throws IOException {
        if (!Files.exists(BASE_DIR)) return List.of();
        // Collect candidate NDVI PNGs only (skip rgb_* quicklooks)
        List<Path> pngs;
        try (Stream<Path> files = Files.walk(BASE_DIR, 1)) {
            pngs = files
                .filter(p -> {
                    String name = p.getFileName().toString();
                    return name.endsWith(".png") && name.startsWith("ndvi_");
                })
                .collect(Collectors.toList());
        }

        // Map to response objects, capturing whether sidecar metadata exists
        List<Map<String, Object>> mapped = new ArrayList<>();
        for (Path p : pngs) {
            Map<String, Object> m = new HashMap<>();
            String fileName = p.getFileName().toString();
            m.put("file", fileName);
            String base = fileName.replaceFirst("\\.png$", "");
            m.put("tif", base + ".tif");
            Path sidecar = BASE_DIR.resolve(base + ".json");
            boolean hasMeta = false;
            if (Files.exists(sidecar)) {
                try {
                    Map<String, Object> meta = MAPPER.readValue(Files.readString(sidecar, StandardCharsets.UTF_8), new TypeReference<Map<String, Object>>(){});
                    if (meta.containsKey("color")) m.put("color", meta.get("color"));
                    if (meta.containsKey("bounds")) m.put("bounds", meta.get("bounds"));
                    if (meta.containsKey("date")) m.put("date", meta.get("date"));
                    if (meta.containsKey("tile")) m.put("tile", meta.get("tile"));
                    if (meta.containsKey("rgb") && meta.get("rgb") != null) m.put("rgb", meta.get("rgb"));
                    if (meta.containsKey("hot") && meta.get("hot") != null) m.put("hot", meta.get("hot"));
                    hasMeta = true;
                } catch (Exception ignored) {}
            }
            m.put("_hasMeta", hasMeta);
            mapped.add(m);
        }

        // Sort: items with metadata first, then by date desc if present, else by filename desc
        mapped.sort((a, b) -> {
            boolean am = Boolean.TRUE.equals(a.get("_hasMeta"));
            boolean bm = Boolean.TRUE.equals(b.get("_hasMeta"));
            if (am != bm) return am ? -1 : 1; // metadata first
            String ad = String.valueOf(a.getOrDefault("date", ""));
            String bd = String.valueOf(b.getOrDefault("date", ""));
            int cmp = bd.compareTo(ad); // date desc
            if (cmp != 0) return cmp;
            String af = String.valueOf(a.getOrDefault("file", ""));
            String bf = String.valueOf(b.getOrDefault("file", ""));
            return bf.compareTo(af); // filename desc
        });

        // Limit and strip internal flag
        return mapped.stream().limit(20).map(m -> {
            m.remove("_hasMeta");
            return m;
        }).collect(Collectors.toList());
    }

    @GetMapping("/search")
    public List<Map<String, Object>> searchNdvi(
            @RequestParam(value = "start", required = false) String start,
            @RequestParam(value = "end", required = false) String end,
            @RequestParam(value = "south", required = false) Double south,
            @RequestParam(value = "west", required = false) Double west,
            @RequestParam(value = "north", required = false) Double north,
            @RequestParam(value = "east", required = false) Double east,
            @RequestParam(value = "limit", required = false, defaultValue = "200") int limit
    ) throws IOException {
        if (!Files.exists(BASE_DIR)) return List.of();
    final boolean hasBbox = south != null && west != null && north != null && east != null;
    final double qs = south != null ? south : 0.0;
    final double qw = west != null ? west : 0.0;
    final double qn = north != null ? north : 0.0;
    final double qe = east != null ? east : 0.0;
        List<Map<String, Object>> results = new ArrayList<>();
        try (Stream<Path> files = Files.walk(BASE_DIR, 1)) {
            List<Path> jsons = files
                    .filter(p -> p.getFileName().toString().endsWith(".json"))
                    .sorted(Comparator.comparing(Path::getFileName).reversed())
                    .limit(limit)
                    .collect(Collectors.toList());
            for (Path sidecar : jsons) {
                try {
                    Map<String, Object> meta = MAPPER.readValue(Files.readString(sidecar, StandardCharsets.UTF_8), new TypeReference<Map<String, Object>>(){});
                    // Filter by date
                    if (start != null || end != null) {
                        String date = (String) meta.getOrDefault("date", "");
                        if (!date.isEmpty()) {
                            if (start != null && date.compareTo(start) < 0) continue;
                            if (end != null && date.compareTo(end) > 0) continue;
                        }
                    }
                    // Filter by bbox intersection
                    if (hasBbox && meta.containsKey("bounds")) {
                        List<?> b = (List<?>) meta.get("bounds");
                        if (b.size() == 4) {
                            double s = ((Number) b.get(0)).doubleValue();
                            double w = ((Number) b.get(1)).doubleValue();
                            double n = ((Number) b.get(2)).doubleValue();
                            double e = ((Number) b.get(3)).doubleValue();
                            boolean disjoint = (e < qw) || (qe < w) || (n < qs) || (qn < s);
                            if (disjoint) continue;
                        }
                    }
                    // Construct output
                    Map<String, Object> out = new HashMap<>();
                    out.put("file", meta.get("file"));
                    String base = sidecar.getFileName().toString().replaceFirst("\\.json$", "");
                    out.put("tif", base + ".tif");
                    if (meta.containsKey("color")) out.put("color", meta.get("color"));
                    if (meta.containsKey("bounds")) out.put("bounds", meta.get("bounds"));
                    if (meta.containsKey("date")) out.put("date", meta.get("date"));
                    if (meta.containsKey("tile")) out.put("tile", meta.get("tile"));
                    if (meta.containsKey("mean")) out.put("mean", meta.get("mean"));
                    if (meta.containsKey("rgb") && meta.get("rgb") != null) out.put("rgb", meta.get("rgb"));
                    if (meta.containsKey("hot") && meta.get("hot") != null) out.put("hot", meta.get("hot"));
                    results.add(out);
                } catch (Exception ignored) {}
            }
        }
        // Sort by date ascending
        results.sort((a, b) -> String.valueOf(a.getOrDefault("date", "")).compareTo(String.valueOf(b.getOrDefault("date", ""))));
        return results;
    }

    @GetMapping("/image")
    public ResponseEntity<FileSystemResource> image(@RequestParam("file") String file) throws IOException {
        // allow only .png files and prevent path traversal
        if (file.contains("..") || !file.endsWith(".png")) {
            return ResponseEntity.badRequest().build();
        }
        Path p = BASE_DIR.resolve(file).normalize();
        if (!p.startsWith(BASE_DIR) || !Files.exists(p)) {
            return ResponseEntity.notFound().build();
        }
    FileSystemResource res = new FileSystemResource(p);
    return ResponseEntity.ok()
        .header(HttpHeaders.CACHE_CONTROL, "no-cache")
        .header(HttpHeaders.CONTENT_TYPE, "image/png")
        .body(res);
    }
}
