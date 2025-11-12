package com.matengine.api.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@RestController
@RequestMapping("/api/ingest")
public class IngestController {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final Path JOBS_DIR = Paths.get("/workspace/data/jobs");

    @GetMapping("/zip")
    public ResponseEntity<Map<String, Object>> ingestByZip(
            @RequestParam("zip") String zip,
            @RequestParam(value = "country", required = false, defaultValue = "us") String country
    ) throws IOException, InterruptedException {
        // Geocode using Nominatim
        String url = String.format(Locale.ROOT,
                "https://nominatim.openstreetmap.org/search?format=json&q=%s&countrycodes=%s&limit=1",
                encode(zip), encode(country));
        HttpClient client = HttpClient.newHttpClient();
        HttpRequest req = HttpRequest.newBuilder(URI.create(url))
                .header("User-Agent", "mat-engine/1.0 (ingest)")
                .GET().build();
        HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() != 200) {
            return ResponseEntity.status(502).body(Map.of("error", "Geocoding failed", "status", resp.statusCode()));
        }
        List<?> arr = MAPPER.readValue(resp.body(), List.class);
        if (arr.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "ZIP not found"));
        }
        Map<?, ?> first = (Map<?, ?>) arr.get(0);
        List<?> bb = (List<?>) first.get("boundingbox"); // [south, north, west, east]
        double south = Double.parseDouble(String.valueOf(bb.get(0)));
        double north = Double.parseDouble(String.valueOf(bb.get(1)));
        double west = Double.parseDouble(String.valueOf(bb.get(2)));
        double east = Double.parseDouble(String.valueOf(bb.get(3)));
        // Create job for 2025 season (adjust as needed)
        Map<String, Object> job = new HashMap<>();
        job.put("bounds", List.of(south, west, north, east));
        job.put("start", "2025-03-01");
        job.put("end", "2025-10-31");
        job.put("max_cloud", 20);
        job.put("limit", 8);
        String jobId = "job_" + Instant.now().toEpochMilli();
        JOBS_DIR.toFile().mkdirs();
        Files.writeString(JOBS_DIR.resolve(jobId + ".json"), MAPPER.writeValueAsString(job), StandardCharsets.UTF_8);
        Map<String, Object> out = new HashMap<>();
        out.put("jobId", jobId);
        out.put("bounds", job.get("bounds"));
        out.put("start", job.get("start"));
        out.put("end", job.get("end"));
        return ResponseEntity.accepted().body(out);
    }

    @GetMapping("/jobs")
    public ResponseEntity<Map<String, Object>> listJobs() throws IOException {
        Files.createDirectories(JOBS_DIR);
        Path done = JOBS_DIR.resolve("done");
        Path failed = JOBS_DIR.resolve("failed");
        Files.createDirectories(done);
        Files.createDirectories(failed);
        var res = new HashMap<String, Object>();
        res.put("pending", Files.list(JOBS_DIR)
                .filter(p -> p.getFileName().toString().endsWith(".json"))
                .map(p -> p.getFileName().toString().replace(".json", ""))
                .toList());
        res.put("done", Files.exists(done) ? Files.list(done)
                .filter(p -> p.getFileName().toString().endsWith(".json"))
                .map(p -> p.getFileName().toString().replace(".json", ""))
                .toList() : List.of());
        res.put("failed", Files.exists(failed) ? Files.list(failed)
                .filter(p -> p.getFileName().toString().endsWith(".json"))
                .map(p -> p.getFileName().toString().replace(".json", ""))
                .toList() : List.of());
        return ResponseEntity.ok(res);
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> jobStatus(@RequestParam("jobId") String jobId) throws IOException {
        Files.createDirectories(JOBS_DIR);
        Path pending = JOBS_DIR.resolve(jobId + ".json");
        Path done = JOBS_DIR.resolve("done").resolve(jobId + ".json");
        Path failed = JOBS_DIR.resolve("failed").resolve(jobId + ".json");
        String status;
        Path where;
        if (Files.exists(pending)) { status = "pending"; where = pending; }
        else if (Files.exists(done)) { status = "done"; where = done; }
        else if (Files.exists(failed)) { status = "failed"; where = failed; }
        else { status = "unknown"; where = null; }
        Map<String, Object> out = new HashMap<>();
        out.put("jobId", jobId);
        out.put("status", status);
        if (where != null) {
            try {
                Map<?,?> j = MAPPER.readValue(Files.readString(where, StandardCharsets.UTF_8), Map.class);
                out.put("job", j);
            } catch (Exception ignore) {}
        }
        return ResponseEntity.ok(out);
    }

    private static String encode(String s) {
        return s.replace(" ", "%20");
    }
}
