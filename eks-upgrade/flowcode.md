flowchart TD
    A["gsm-terraform-helm v20 - shared defaults<br/>pricer port 61616 ON<br/>healthcheck port 10254<br/>preserve_client_ip false"]

    A --> E1
    A --> F1

    subgraph metal["gsm-metal repo"]
        E1["common.tfvars - ALL metal envs<br/>tcp.61616 = null<br/>ports.pricer = null<br/>healthcheck-port = 80<br/>preserve_client_ip = true<br/>TCS header buffers = 128k"]
        E2["dst.tfvars - dst only<br/>dns_record_weight = 0"]
        E3["Final metal settings<br/>no pricer port<br/>healthcheck 80<br/>client IP preserved"]
        E1 -->|"deep merge"| E2
        E2 --> E3
    end

    subgraph tacets["gsm-tacets repo"]
        F1["tacets tfvars<br/>no overrides"]
        F2["Final tacets settings<br/>pricer port ON<br/>healthcheck 10254"]
        F1 --> F2
    end

    E3 --> SVC["K8s Service ingress-nginx-controller<br/>port 443 only"]
    SVC -->|"LB Controller reads annotations"| NLB["NLB target group<br/>health check port 80<br/>client IP preserved"]
    NLB --> OK["Targets healthy - metal UI works"]

    style A fill:#fde2e2,stroke:#c0392b
    style E1 fill:#e2f0fd,stroke:#2471a3
    style E2 fill:#e8f8e8,stroke:#27ae60
    style E3 fill:#fff8dc,stroke:#b7950b
    style F2 fill:#fff8dc,stroke:#b7950b
    style OK fill:#d5f5e3,stroke:#1e8449

==========================================


flowchart LR
    subgraph TF["common.tfvars lines"]
        L1["tcp.61616 = null<br/>ports.pricer = null"]
        L2["healthcheck-port = 80"]
        L3["target-group-attributes =<br/>preserve_client_ip.enabled=true"]
        L4["client-header-buffer-size<br/>large-client-header-buffers"]
    end

    subgraph K8S["Kubernetes"]
        SVC["ingress-nginx-controller Service<br/>only port 443"]
        NGX["nginx config<br/>big headers allowed"]
    end

    subgraph AWS["AWS - via Load Balancer Controller"]
        NLB["NLB listener 443 only"]
        TG["Target group<br/>health check on port 80<br/>client IP preserved"]
    end

    L1 -->|"removes port Metal does not have"| SVC
    L2 -->|"annotation on Service"| SVC
    L3 -->|"annotation on Service"| SVC
    L4 --> NGX
    SVC -->|"LB Controller reads annotations"| NLB
    SVC --> TG
    TG -->|"targets healthy"| OK["Metal UI works"]
    NGX --> OK

    style L1 fill:#fde2e2,stroke:#c0392b
    style L2 fill:#e2f0fd,stroke:#2471a3
    style L3 fill:#e2f0fd,stroke:#2471a3
    style L4 fill:#e8f8e8,stroke:#27ae60
    style SVC fill:#fff8dc,stroke:#b7950b
    style NGX fill:#fff8dc,stroke:#b7950b
    style OK fill:#d5f5e3,stroke:#1e8449
