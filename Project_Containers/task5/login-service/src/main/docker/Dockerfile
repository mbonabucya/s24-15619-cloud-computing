FROM maven:3.8.4-jdk-8-slim
WORKDIR /app
COPY pom.xml .
COPY . .
RUN mvn clean package
EXPOSE 8080
CMD ["java", "-jar", "/app/target/login-0.1.0.jar"]
