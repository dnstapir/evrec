# DNS TAPIR Event Receiver

This repository contains the DNS TAPIR Event Receiver, a server component use for retrieving and validating TAPIR events.


## Configuration

The default configuration file is `evrec.toml`. Example configuration below:

    clients_database = "clients"
    schema_validation = true

    [mqtt]
    broker = "mqtt://localhost"
    topic_read = "events/up/#"
    topic_write = "verified"
    reconnect_interval = 5
