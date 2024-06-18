# DNS TAPIR Event Receiver

This repository contains the DNS TAPIR Event Receiver, a server component use for retrieving and validating TAPIR events.


## Configuration

    CLIENTS_DATABASE = "clients"
    MQTT_BROKER = "localhost"
    MQTT_TOPIC_READ = "events/up/#"
    MQTT_TOPIC_WRITE = "verified"
    SCHEMA_VALIDATION = true
