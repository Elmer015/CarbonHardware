# Architecture Diagram

Diagram berikut menggambarkan implementasi CarbonHardware yang ditemukan pada kode dan konfigurasi workspace.

## Application Architecture

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
~~~mermaid
flowchart TD
    subgraph ClientLayer["Client Layer"]
        Browser["Web browser"]
        ReactUI["React and Vite frontend"]
    end
    subgraph BackendLayer["Backend Layer"]
        Api["Node.js and Express REST API"]
        Domain["Carbon and comparison services"]
        PythonBridge["Python subprocess bridge"]
    end
    subgraph DataLayer["Local Data Layer"]
        CarbonSet[("CarbonSet CSV")]
        GridData[("OWID Ember CSV")]
        StecData[("STEC evidence and output CSV")]
        ModelArtifact[("Joblib model artifact")]
    end
    subgraph EngineLayer["Python Engine"]
        Embodied["Embodied carbon model"]
        StecEngine["STEC calculator"]
    end

    Browser -->|"user interaction"| ReactUI
    ReactUI -->|"HTTP JSON requests"| Api
    Api -->|"loads hardware"| CarbonSet
    Api -->|"loads grid factors"| GridData
    Api -->|"loads STEC inventory"| StecData
    Api -->|"calculations and lookups"| Domain
    Domain -->|"JSON input and output"| PythonBridge
    PythonBridge -->|"prediction request"| Embodied
    PythonBridge -->|"STEC request"| StecEngine
    Embodied -->|"reads"| ModelArtifact
    Api -->|"response JSON"| ReactUI
~~~

### Technology Stack Summary

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Frontend | React, Vite, JSX, CSS | React 18; Vite 6 | Forms, navigation, estimates, STEC and comparison pages |
| Backend | Node.js, Express, CORS | Express 5 | REST API, validation, CSV loading and service orchestration |
| Model and calculation engine | Python, scikit-learn, pandas, NumPy, joblib | Python package versions are environment dependent | Embodied carbon inference and carbon accounting calculations |
| Data | Local CSV and JSON files | Snapshot and artifact versions are recorded separately | CarbonSet, grid factors, STEC evidence and results |
| Database | No active runtime database connection identified | Not applicable | A schema file exists but is not part of the observed API runtime flow |

### Data Storage & External Services

The backend loads CarbonSet, lifecycle electricity intensity and STEC inventory from local files. The embodied model is loaded from a local Joblib artifact. Node.js calls Python through a subprocess and JSON standard input/output. The observed frontend calls the local backend through HTTP. No active runtime database, cache service, or external API call was identified in the traced application path. The local OWID/Ember CSV is a downloaded snapshot, not a live API integration.

### Key Architectural Decisions

- The backend uses REST endpoints and service/controller separation.
- Python calculations are invoked as subprocesses rather than through a separate Python web server.
- Missing grid data and unsupported STEC evidence produce explicit errors or incomplete statuses rather than guessed fallback values.

## Component Relationships

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
~~~mermaid
flowchart LR
    subgraph cPresentation["Presentation"]
        cEstimatePage["EstimateCarbon page"]
        cHardwareForm["HardwareForm"]
        cStecPage["StecResults page"]
        cComparePage["Comparison page"]
        cApiClient["Frontend fetch requests"]
    end
    subgraph cApplication["API and Domain Services"]
        cRoutes["Express route modules"]
        cControllers["Estimate and STEC controllers"]
        cHardwareSvc["Hardware loader"]
        cGridSvc["Grid intensity service"]
        cComparisonSvc["Comparison service"]
        cCarbonSvc["Carbon and CCI services"]
        cPythonSvc["Python service bridge"]
        cMiddleware["Error middleware"]
    end
    subgraph cDataEngine["Files and Calculation Engine"]
        cCarbonCsv[("CarbonSet CSV")]
        cGridCsv[("Grid intensity CSV")]
        cStecCsv[("STEC inventory CSV")]
        cJoblib[("Embodied model artifact")]
        cEmbodiedPy["Embodied prediction module"]
        cStecPy["STEC calculation module"]
    end

    cEstimatePage -->|"uses"| cHardwareForm
    cEstimatePage -->|"sends requests"| cApiClient
    cStecPage -->|"sends requests"| cApiClient
    cComparePage -->|"sends requests"| cApiClient
    cApiClient -->|"HTTP JSON"| cRoutes
    cRoutes -->|"dispatches"| cControllers
    cControllers -->|"processor lookup"| cHardwareSvc
    cControllers -->|"region and year lookup"| cGridSvc
    cControllers -->|"energy and CCI"| cCarbonSvc
    cControllers -->|"prediction and STEC"| cPythonSvc
    cControllers -->|"comparison request"| cComparisonSvc
    cHardwareSvc -->|"reads"| cCarbonCsv
    cGridSvc -->|"reads"| cGridCsv
    cComparisonSvc -->|"joins inventory"| cStecCsv
    cComparisonSvc -->|"batch inference"| cPythonSvc
    cPythonSvc -->|"loads"| cJoblib
    cPythonSvc -->|"calls"| cEmbodiedPy
    cPythonSvc -->|"calls"| cStecPy
    cMiddleware -.->|"handles API errors"| cRoutes
~~~

### Component Inventory

| Component | Layer | Type | Responsibility |
|---|---|---|---|
| EstimateCarbon | Presentation | React page | Collects processor, usage scenario and CCI inputs; displays estimates and embodied-only screening candidates |
| HardwareForm | Presentation | React component | Existing/custom processor form and operational assumptions |
| StecResults | Presentation | React page | Selects STEC inventory item or submits custom die scenario |
| Comparison | Presentation | React page | Displays embodied model result and STEC side-by-side |
| Express route modules | API | Routes | Map HTTP paths to controllers |
| Estimate and STEC controllers | API | Controllers | Validate request shape, select services and form responses |
| Hardware loader | Data access | Service | Loads CarbonSet processor records |
| Grid intensity service | Data access | Service | Loads and finds country-year lifecycle grid factors |
| Comparison service | Domain | Service | Joins embodied predictions to STEC records |
| Carbon and CCI services | Domain | Services | Compute operational energy, operational carbon and carbon per workload |
| Python service bridge | Integration | Service | Invokes Python calculators and model prediction using JSON |
| Error middleware | Cross-cutting | Middleware | Returns consistent API error responses |
| CarbonSet and grid CSV files | Data | Local datasets | Hardware features, targets and grid intensity lookup values |
| STEC inventory CSV | Data | Derived dataset | Per-processor point, range or incomplete STEC result |
| Joblib artifact | Model data | Serialized model | Trained experimental embodied-carbon estimator |
| Embodied and STEC Python modules | Calculation | Python modules | Predict embodied carbon and calculate die STEC |
