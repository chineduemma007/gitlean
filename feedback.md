# Paritok API & Proxy Diagnostics (Hackathon Feedback)

This file tracks all bugs, validation issues, edge cases, and documentation errors discovered in the Paritok API, proxy server, and model behavior during the development of GitLean.

---

## 1. Initial Findings (Prior Audits & Search Context)

### Issue 1: "Pin-on-Expand" Token Overspend
- **Description**: When a coding agent calls an `expand_context` or similar tool that requests the full uncompressed context of a file, the Paritok proxy initially compresses it, bills for the compression, but then passes the full uncompressed context to the model anyway.
- **Impact**: Double-billing or redundant processing of tokens when a full pass-through is requested.
- **Suggested Fix**: implement a "pinning" mechanism where once a file/segment is requested in full, the proxy bypasses the compression layer entirely for that segment, returning it verbatim without duplicate token billing.

### Issue 2: Parameter Validation Gaps on Hosted Endpoint
- **Description**: The Paritok hosted endpoint does not strictly validate input parameters. For example, passing an invalid compression level (e.g., `"level": "BANANA"`) returns a `200 OK` rather than a `400 Bad Request`.
- **Impact**: Developers may have silent failures or misconfigurations where compression parameters are ignored and default values are applied without warning.
- **Suggested Fix**: Strict schema validation on incoming JSON payloads.

---

## 2. Real-Time Findings (Encountered during development)

### Issue 3: Missing Auth Headers in `GpuServerStrategy.check()` (Startup False Failures)
- **File**: `paritok/strategies/gpu_server.py`
- **Description**: While the `compress()` method correctly attaches the `Authorization: Bearer <api_key>` header to its HTTP POST requests, the `check()` method (used for startup health verification) makes a request to the hosted endpoint without passing any credentials. If the hosted server's health route requires authentication (or checks for valid keys), this check fails, causing `paritok up` to report the hosted GPU server as unreachable, even though actual compression calls would succeed.
- **Impact**: Silent or false-positive startup crashes when `use_gpu_server: true` is enabled in `paritok.yaml`.
- **Suggested Fix**: Update `GpuServerStrategy.check()` to pull the configured API key and pass it in the `Authorization: Bearer <key>` header, matching the request pattern in `compress()`.

