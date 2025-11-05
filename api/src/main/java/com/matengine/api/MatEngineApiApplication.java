package com.matengine.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class MatEngineApplication {

    public static void main(String[] args) {
        SpringApplication.run(MatEngineApplication.class, args);
    }

    @GetMapping("/api/ping")
    public String ping() {
        return "{\"status\": \"ok\", \"message\": \"MAT Engine API running\"}";
    }
}
