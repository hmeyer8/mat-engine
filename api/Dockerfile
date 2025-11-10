FROM eclipse-temurin:21-jdk AS build
WORKDIR /app

# Copy Gradle wrapper & project files
COPY gradlew gradlew.bat ./
COPY gradle gradle
COPY build.gradle.kts .
COPY settings.gradle.kts .
COPY src src

# Ensure gradlew uses Unix LF and is executable
RUN sed -i 's/\r$//' gradlew && chmod +x gradlew

# Build the JAR
RUN ./gradlew bootJar --no-daemon

# ---------- Runtime Stage ----------
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/build/libs/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
