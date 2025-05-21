# Tenant-Specific Configuration Guide

This directory contains configuration files and code that can be customized per tenant. Each tenant will have their own directory with custom configurations for:

- MediaMTX camera paths
- Sampling logic (when to sample frames from video streams)
- Inference logic (what to detect and how to process detections)

## Directory Structure

```
tenants/
├── default/              # Default tenant configuration (used as template)
│   ├── configs/          # Configuration files
│   │   └── mediamtx.yml  # MediaMTX configuration 
│   ├── sampler/          # Custom frame sampling logic
│   │   └── default_sampler.py
│   └── inference/        # Custom inference and event detection
│       └── default_inference.py
├── tenant1/              # Example tenant-specific configuration
│   ├── configs/
│   ├── sampler/
│   └── inference/
└── README.md             # This file
```

## Running with a Specific Tenant

To run the system with a specific tenant configuration, set the `TENANT_ID` environment variable:

```bash
TENANT_ID=tenant1 docker compose up -d
```

If `TENANT_ID` is not specified, the system will use the `default` tenant configuration.