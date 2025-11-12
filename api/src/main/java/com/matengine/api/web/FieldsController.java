package com.matengine.api.web;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@RestController
@RequestMapping("/api/fields")
public class FieldsController {

    private static final Path BASE_DIR = Paths.get("/workspace/data/processed/sentinel-2");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @GetMapping("/list")
    public List<Map<String, Object>> listFields() throws IOException {
        if (!Files.exists(BASE_DIR)) return List.of();
        // Aggregate unique fields by bounds present in NDVI sidecar JSONs
        Map<String, FieldAgg> byBounds = new HashMap<>();
        try (Stream<Path> files = Files.walk(BASE_DIR, 1)) {
            List<Path> jsons = files
                    .filter(p -> p.getFileName().toString().endsWith(".json"))
                    .collect(Collectors.toList());
            for (Path sidecar : jsons) {
                try {
                    Map<String, Object> meta = MAPPER.readValue(Files.readString(sidecar, StandardCharsets.UTF_8), new TypeReference<Map<String, Object>>(){});
                    if (!meta.containsKey("bounds")) continue;
                    @SuppressWarnings("unchecked")
                    List<Object> b = (List<Object>) meta.get("bounds");
                    if (b.size() != 4) continue;
                    // normalize to 6 decimal places for stable key
                    double s = ((Number) b.get(0)).doubleValue();
                    double w = ((Number) b.get(1)).doubleValue();
                    double n = ((Number) b.get(2)).doubleValue();
                    double e = ((Number) b.get(3)).doubleValue();
                    String key = String.format(Locale.ROOT, "%.6f,%.6f,%.6f,%.6f", s, w, n, e);
                    String date = String.valueOf(meta.getOrDefault("date", ""));
                    FieldAgg agg = byBounds.getOrDefault(key, new FieldAgg(s, w, n, e));
                    agg.count += 1;
                    if (!date.isEmpty()) {
                        if (agg.minDate == null || date.compareTo(agg.minDate) < 0) agg.minDate = date;
                        if (agg.maxDate == null || date.compareTo(agg.maxDate) > 0) agg.maxDate = date;
                    }
                    byBounds.put(key, agg);
                } catch (Exception ignored) {}
            }
        }
        // Map to response with stable id
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map.Entry<String, FieldAgg> e : byBounds.entrySet()) {
            FieldAgg a = e.getValue();
            Map<String, Object> m = new HashMap<>();
            m.put("id", Integer.toHexString(e.getKey().hashCode()));
            m.put("bounds", List.of(a.s, a.w, a.n, a.e));
            m.put("count", a.count);
            if (a.minDate != null) m.put("minDate", a.minDate);
            if (a.maxDate != null) m.put("maxDate", a.maxDate);
            out.add(m);
        }
        // Sort by count desc, then date desc
        out.sort((a, b) -> {
            int ca = ((Number) a.getOrDefault("count", 0)).intValue();
            int cb = ((Number) b.getOrDefault("count", 0)).intValue();
            if (cb != ca) return Integer.compare(cb, ca);
            String ad = String.valueOf(a.getOrDefault("maxDate", ""));
            String bd = String.valueOf(b.getOrDefault("maxDate", ""));
            return bd.compareTo(ad);
        });
        return out;
    }

    private static class FieldAgg {
        double s; double w; double n; double e;
        int count = 0;
        String minDate; String maxDate;
        FieldAgg(double s, double w, double n, double e) {
            this.s = s; this.w = w; this.n = n; this.e = e;
        }
    }
}
