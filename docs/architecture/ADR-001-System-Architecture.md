# ADR-001: Alcohol Label Verification PoC — System Architecture

**Status:** Proposed  
**Date:** 2026-06-09  
**Deciders:** Engineering Lead, Product Owner, Treasury Review Team

---

## Context

The TTB (Alcohol and Tobacco Tax and Trade Bureau) currently employs 47 human reviewers processing ~150,000 COLA (Certificate of Label Approval) applications annually. The manual process is bottlenecked on routine data-entry verification — comparing what's printed on a physical label against what was submitted in the application form. This PoC automates that verification step using AI-powered OCR and semantic matching, running in a firewalled government environment.

**Key constraints driving every architectural decision:**
- Strict outbound firewall — no guaranteed internet access
- No integration with legacy .NET COLA system
- No persistent storage of PII or label images
- Must process 1 label in ≤ 5 seconds
- Must handle bulk batches of 200–300 labels
- UI must be operable by users with very low technical literacy

---

## Decision

Build a **containerized, single-node web application** with a React frontend, a Python FastAPI backend, a local vision/OCR engine (Claude Vision via whitelisted endpoint or local Tesseract fallback), and an in-memory processing pipeline. No external database. No persistent image storage.

---

## Options Considered

### Option A: Cloud-first (OpenAI / Anthropic API + cloud DB)
| Dimension | Assessment |
|-----------|------------|
| OCR Accuracy | High |
| Latency | Medium (network round-trip) |
| Firewall Risk | **High — likely blocked** |
| PII Risk | **High — images leave the network** |
| Setup Complexity | Low |

**Pros:** Best-in-class vision models, minimal local compute needed  
**Cons:** Outbound firewall likely blocks it; images containing PII/business data leave the facility — regulatory risk

### Option B: Fully local (Tesseract + local fuzzy match)
| Dimension | Assessment |
|-----------|------------|
| OCR Accuracy | Medium |
| Latency | Very Low |
| Firewall Risk | None |
| PII Risk | None |
| Setup Complexity | Medium |

**Pros:** Air-gapped safe, fast, no data leaves machine  
**Cons:** Tesseract struggles with real-world label photos (glare, curves, low-res)

### Option C: Hybrid — local primary, whitelisted API fallback ✅ **Recommended**
| Dimension | Assessment |
|-----------|------------|
| OCR Accuracy | High (API path) / Medium (local fallback) |
| Latency | ~3–5s (API) / ~1–2s (local) |
| Firewall Risk | Low — only 1 whitelisted endpoint needed |
| PII Risk | Low — images are ephemeral, not stored |
| Setup Complexity | Medium |

**Pros:** Works in both firewalled and open environments; graceful degradation; single whitelisted endpoint minimizes security surface  
**Cons:** Requires IT to whitelist one API endpoint; slight complexity in dual-path logic

---

## Trade-off Analysis

The firewall constraint eliminates pure cloud solutions. A fully local Tesseract approach risks unacceptable OCR accuracy on real-world label photos (curved bottles, glare, partial obstruction). The hybrid model — attempt the whitelisted vision API, fall back to local Tesseract if blocked — satisfies both accuracy and reliability requirements. Since images are processed ephemerally (never written to disk or sent to a database), PII exposure is limited to the in-flight API call, which can be isolated to a single whitelisted domain.

---

## Consequences

- Deployment is a single Docker container — IT installs once, no ongoing cloud dependency
- If IT cannot whitelist the API endpoint, OCR quality degrades but the system still functions
- No horizontal scaling needed for PoC; single-node handles the 200–300 batch requirement via async parallel processing
- Zero long-term data retention — reviewers must export/download results before closing the session

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React + Tailwind CSS | Fast to build, accessible, single-page |
| Backend API | Python FastAPI | Async support, fast, easy AI library integration |
| Vision / OCR | Claude Vision API (primary) + Tesseract (fallback) | Best accuracy with local safety net |
| Matching Engine | RapidFuzz (Python) | Industry-standard fuzzy matching, MIT license |
| Batch Orchestrator | Python asyncio + concurrent.futures | Parallel label processing without external queue |
| In-Memory Cache | Python dict / Redis (optional) | Ephemeral result storage for session |
| Containerization | Docker + Docker Compose | Single-command deployment |

---

## Action Items

1. [ ] Set up monorepo: `/frontend`, `/backend`, `/docker`
2. [ ] Scaffold FastAPI app with `/verify`, `/verify/batch`, `/health` endpoints
3. [ ] Implement OCR adapter: tries Claude Vision, catches network error, falls back to Tesseract
4. [ ] Implement RapidFuzz matching engine with per-field rules (fuzzy vs. exact)
5. [ ] Build React review UI: upload → results side-by-side → export CSV
6. [ ] Implement batch orchestrator with progress streaming (SSE or WebSocket)
7. [ ] Write Dockerfile + docker-compose.yml
8. [ ] Load test: 300 labels, verify ≤ 5s average, no crashes
9. [ ] Accessibility pass: keyboard nav, WCAG AA contrast, large tap targets

---

## System Architecture Diagram

> **How to read this diagram:** Follow the flow from left (User) to right (AI Engine). Each box is a component of the system. Arrows show how data moves. Color bands show which "layer" each component belongs to.

```mermaid
graph TB
    subgraph UI["🖥️  PRESENTATION LAYER — What the reviewer sees"]
        A["👤 Reviewer\n(uploads label photo\nand application data)"]
        B["📱 Web Browser\n(React App)\n• Upload screen\n• Results screen\n• Batch progress"]
    end

    subgraph API["⚙️  API LAYER — The traffic controller"]
        C["🔀 Backend API\n(FastAPI)\n• Receives uploads\n• Routes requests\n• Returns results"]
    end

    subgraph PROC["🧠  PROCESSING LAYER — Where the intelligence lives"]
        D["👁️ OCR / Vision Engine\n• Reads text from label photo\n• Handles glare & angles\n• Returns extracted fields"]
        E["⚖️ Matching Engine\n• Fuzzy match (brand, address)\n• Exact match (Govt. Warning)\n• Scores each field"]
    end

    subgraph ORCH["🔄  ORCHESTRATION LAYER — Manages bulk work"]
        F["📦 Batch Orchestrator\n• Splits 200–300 labels\n  into parallel workers\n• Streams progress updates"]
    end

    subgraph DATA["💾  DATA LAYER — Temporary memory only"]
        G["🗂️ In-Memory Cache\n• Holds results for\n  current session only\n• Nothing saved to disk"]
    end

    subgraph EXT["🌐  EXTERNAL (Optional / Whitelisted)"]
        H["☁️ Claude Vision API\n(1 whitelisted endpoint)\nHigh-accuracy OCR"]
        I["💻 Local Tesseract\n(offline fallback)\nWorks with no internet"]
    end

    A -->|"📸 Upload label image\n+ application data"| B
    B -->|"HTTPS POST"| C
    C -->|"Single label"| D
    C -->|"Batch of labels"| F
    F -->|"Parallel workers"| D
    D -->|"Try cloud first"| H
    H -->|"Blocked by firewall?"| I
    D -->|"Extracted text fields"| E
    E -->|"Match results\n+ confidence scores"| C
    C -->|"Store session results"| G
    C -->|"Verification report"| B
    G -->|"Retrieved on request"| C

    style UI fill:#dbeafe,stroke:#3b82f6,color:#1e40af
    style API fill:#dcfce7,stroke:#16a34a,color:#14532d
    style PROC fill:#fef9c3,stroke:#ca8a04,color:#713f12
    style ORCH fill:#fce7f3,stroke:#db2777,color:#831843
    style DATA fill:#f3e8ff,stroke:#9333ea,color:#581c87
    style EXT fill:#f1f5f9,stroke:#64748b,color:#334155
```

---

## Sequence Diagram — Single Label Verification

> **How to read this:** Time flows downward. Each vertical line is a system component. Arrows are messages passed between them.

```mermaid
sequenceDiagram
    actor Reviewer as 👤 Reviewer
    participant UI as 🖥️ Web App
    participant API as ⚙️ Backend API
    participant OCR as 👁️ OCR Engine
    participant Vision as ☁️ Claude Vision
    participant Tess as 💻 Tesseract
    participant Match as ⚖️ Matching Engine
    participant Cache as 🗂️ Cache

    Reviewer->>UI: Upload label image + paste application data
    UI->>UI: Validate file type & size
    UI->>API: POST /verify {image, application_data}
    API->>API: Generate session_id, log request

    API->>OCR: extract_fields(image)
    OCR->>Vision: Attempt cloud vision API call
    alt Cloud API available (whitelisted)
        Vision-->>OCR: Return structured field data
    else Network blocked / timeout
        OCR->>Tess: Fallback to local Tesseract
        Tess-->>OCR: Return raw OCR text
        OCR->>OCR: Parse raw text into fields
    end
    OCR-->>API: extracted_fields + image_quality_score

    API->>Match: compare(extracted_fields, application_data)
    Match->>Match: Fuzzy match: brand, class, ABV, address, origin
    Match->>Match: Exact match: Government Warning text
    Match->>Match: Score each field (0–100%)
    Match-->>API: match_results {field, status, score, discrepancy}

    API->>Cache: store(session_id, match_results)
    API-->>UI: VerificationReport {fields[], overall_status, confidence}

    UI->>UI: Render side-by-side comparison
    UI-->>Reviewer: Show results (✅ Match / ⚠️ Partial / ❌ Mismatch)

    opt Reviewer downloads report
        Reviewer->>UI: Click "Export CSV"
        UI->>API: GET /results/{session_id}/export
        API->>Cache: retrieve(session_id)
        Cache-->>API: match_results
        API-->>UI: CSV file
        UI-->>Reviewer: Browser downloads CSV
    end
```

---

## Sequence Diagram — Batch Processing (200–300 Labels)

```mermaid
sequenceDiagram
    actor Reviewer as 👤 Reviewer
    participant UI as 🖥️ Web App
    participant API as ⚙️ Backend API
    participant Orch as 🔄 Batch Orchestrator
    participant W1 as ⚙️ Worker 1
    participant W2 as ⚙️ Worker 2
    participant WN as ⚙️ Worker N
    participant Cache as 🗂️ Cache

    Reviewer->>UI: Upload ZIP of label images + CSV of application data
    UI->>API: POST /verify/batch {images[], applications[]}
    API->>Orch: start_batch(job_id, label_pairs[])
    Orch-->>API: job_id (immediate response)
    API-->>UI: 202 Accepted — {job_id}
    UI->>UI: Show progress bar (poll or stream)

    par Parallel processing
        Orch->>W1: process(label_1, app_data_1)
        Orch->>W2: process(label_2, app_data_2)
        Orch->>WN: process(label_N, app_data_N)
    end

    W1-->>Orch: result_1
    W2-->>Orch: result_2
    WN-->>Orch: result_N

    Orch->>Orch: Aggregate results, compute batch summary
    Orch->>Cache: store(job_id, all_results)

    loop Progress updates (SSE stream)
        Orch-->>UI: {completed: N, total: 300, latest_result}
    end

    Orch-->>UI: Batch complete — {job_id, summary}
    UI-->>Reviewer: Show batch results table
    Reviewer->>UI: Export full batch report (CSV / Excel)
```

---

## Data Flow Diagram

> **How to read this:** Rectangles are processes. Rounded rectangles are data stores. Arrows show what data moves where. Circles are external actors.

```mermaid
flowchart TD
    subgraph INPUT["📥 INPUT — What enters the system"]
        R(["👤 Reviewer"])
        LI["🖼️ Label Image\nJPEG / PNG / PDF"]
        AD["📋 Application Data\nBrand, ABV, Address,\nWarning text, etc."]
    end

    subgraph EXTRACT["🔍 EXTRACTION — Reading the label"]
        QA["🔦 Image Quality\nAssessment\n• Check resolution\n• Detect glare/angle\n• Return quality score"]
        OCR["👁️ OCR / Vision\nProcessing\n• Extract all visible text\n• Identify field regions\n• Normalize text"]
        FP["📐 Field Parser\n• Split text into fields\n• Brand / ABV / Address\n• Government Warning"]
    end

    subgraph MATCH["⚖️ MATCHING — Comparing label to application"]
        FM["🔀 Fuzzy Matcher\n• Brand Name\n• Class / Type\n• Net Contents\n• Name & Address\n• Country of Origin"]
        EM["🎯 Exact Matcher\n• Government Warning\n  word-for-word\n• ALL-CAPS check\n• Bold formatting check"]
        SC["📊 Score Calculator\n• Per-field confidence\n• Overall match score\n• Flag discrepancies"]
    end

    subgraph OUTPUT["📤 OUTPUT — What the reviewer gets back"]
        VR["📄 Verification Report\n• Field-by-field status\n• ✅ Match\n• ⚠️ Partial Match\n• ❌ No Match\n• Confidence %"]
        UI2["🖥️ Review UI\nSide-by-side view"]
        EX["⬇️ Export\nCSV / Excel download"]
    end

    subgraph STORE["💾 TEMPORARY STORAGE — Session only, no disk write"]
        MEM[("🗂️ In-Memory Cache\nResults held for\ncurrent session only\nAuto-cleared on close")]
    end

    R -->|"Uploads"| LI
    R -->|"Enters or uploads"| AD
    LI --> QA
    LI --> OCR
    QA -->|"Quality score\nattached to result"| VR
    OCR --> FP
    FP -->|"Extracted fields"| FM
    FP -->|"Warning text"| EM
    AD -->|"Application fields"| FM
    AD -->|"Expected warning"| EM
    FM --> SC
    EM --> SC
    SC --> VR
    VR --> MEM
    VR --> UI2
    UI2 -->|"Reviews & approves"| R
    UI2 -->|"Export request"| EX
    MEM -->|"Retrieved for export"| EX
    EX -->|"Downloads report"| R

    style INPUT fill:#dbeafe,stroke:#3b82f6,color:#1e40af
    style EXTRACT fill:#fef9c3,stroke:#ca8a04,color:#713f12
    style MATCH fill:#dcfce7,stroke:#16a34a,color:#14532d
    style OUTPUT fill:#fce7f3,stroke:#db2777,color:#831843
    style STORE fill:#f3e8ff,stroke:#9333ea,color:#581c87
```

---

## Implementation Plan

### Phase 1 — Foundation (Week 1)
- [ ] Monorepo setup: `/frontend`, `/backend`, `/docs`, `/docker`
- [ ] FastAPI skeleton: `/health`, `/verify`, `/verify/batch` endpoints
- [ ] Docker + docker-compose: single `docker-compose up` starts everything
- [ ] Basic React shell: upload form + placeholder results panel

### Phase 2 — Core Intelligence (Week 2)
- [ ] OCR adapter: Claude Vision primary → Tesseract fallback
- [ ] Field parser: extract Brand, ABV, Address, Warning, Origin, Net Contents
- [ ] RapidFuzz matching engine with per-field rules
- [ ] Government Warning exact-match validator (word-for-word + formatting)
- [ ] Confidence scoring per field

### Phase 3 — Batch & UI (Week 3)
- [ ] Batch orchestrator: asyncio workers, SSE progress stream
- [ ] React review UI: side-by-side comparison, color-coded field status
- [ ] In-memory cache: store session results, serve export
- [ ] CSV / Excel export endpoint

### Phase 4 — Hardening (Week 4)
- [ ] Imperfect image handling: pre-process with OpenCV (deskew, denoise)
- [ ] Error handling: malformed images, partial OCR, API timeouts
- [ ] Load test: 300 labels, verify ≤ 5s average, zero crashes
- [ ] Accessibility audit: WCAG AA, keyboard nav, large click targets
- [ ] Documentation: README, setup guide, architecture docs (this file)

---

## Appendix — Field Matching Rules Reference

| Field | Match Type | Threshold | Notes |
|-------|-----------|-----------|-------|
| Brand Name | Fuzzy | ≥ 90% | Case & punctuation insensitive |
| Class / Type | Fuzzy | ≥ 85% | Synonym variants allowed |
| ABV / Proof | Exact numeric | ±0.5% tolerance | Parse number from "X% Alc. by Vol." |
| Net Contents | Fuzzy numeric | ±1% tolerance | Handle "750mL" vs "750 ml" |
| Name & Address | Fuzzy | ≥ 80% | Street abbreviations, spacing |
| Country of Origin | Fuzzy | ≥ 90% | "Product of USA" ≈ "United States" |
| Government Warning | **Exact** | 100% | Word-for-word; ALL-CAPS "GOVERNMENT WARNING"; bold prefix required |
