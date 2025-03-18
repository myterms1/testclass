# Use the base image
FROM registry-dev.xyz.com/app-base:latest

# Set argument for JAR file
ARG JAR_FILE="target/app.jar"

# Copy the JAR file into the container
COPY ${JAR_FILE} /opt/application/app.jar

# Set the ENTRYPOINT to run the Java application and then sleep for 5 minutes
ENTRYPOINT ["sh", "-c", "java -jar /opt/application/app.jar && echo 'Waiting for 5 minutes...' && sleep 300"]