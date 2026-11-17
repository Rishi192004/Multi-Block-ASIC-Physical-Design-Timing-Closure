# EDA-Genius: Architectural Specification & Foundation Design

**Project Name:** EDA-Genius: AI-Powered EDA Intelligence & Predictive Optimization Platform  
**Target Domain:** Semiconductor Design Automation / CAD AI / ML-assisted Electronic Design Automation (EDA)  
**Author:** EDA Infrastructure & ML Systems Architecture Lead  
**Document Version:** 1.0.0  
**Status:** Approved for Foundation Review  

---

## 1. System Architecture Diagram

```mermaid
flowchart TD
    subgraph UI_Layer ["Presentation & Analytics Layer"]
        Dashboard["React Frontend Dashboard<br/>• Run Visualizer & Timeline<br/>• Pareto Frontier Plots<br/>• RAG Debugger Console"]
    end

    subgraph API_Layer ["API & Service Layer (FastAPI)"]
        API["FastAPI Orchestration Gateway<br/>• REST Endpoints<br/>• Streaming Logs (WebSocket/SSE)<br/>• Job Submission & State Query"]
    end

    subgraph Core_Engines ["Core EDA & ML Infrastructure"]
        Orchestrator["1. EDA Orchestration Engine<br/>• Yosys RTL Synthesis Driver<br/>• OpenROAD Physical Design Driver<br/>• Artifact & Provenance Tracker"]
        
        LogParser["5. EDA Log Intelligence Engine<br/>• OpenSTA / Yosys Regex & State Parsers<br/>• Lineage & Offset Byte Tracker<br/>• DRC/Timing/Power Extractors"]
        
        FeatureExtractor["2. RTL & Netlist Feature Extractor<br/>• AST / Gate-Level Graph Metrics<br/>• Rent's Exponent & Interconnect Heuristics<br/>• Fanout & Logic Depth Profiles"]
        
        DatasetMgr["3. Experiment Dataset Manager<br/>• Lineage Tracking & Provenance<br/>• Train / Validation / Test Partitions<br/>• Parquet / Arrow Feature Stores"]
        
        MLEngine["4. ML Prediction Engine<br/>• XGBoost / LightGBM Regressors<br/>• Timing (WNS/TNS) Surrogates<br/>• Power & Congestion Predictors<br/>• SHAP Interpretability"]
        
        AnomalyDet["6. Anomaly Detection Engine<br/>• Unsupervised Runtime/Density Outliers<br/>• GRC Routing Congestion Spikes<br/>• Clock Skew & CTS Divergence Checks"]
        
        RAGAssist["7. RAG Diagnostic Assistant<br/>• Local Ollama (Qwen2.5-Coder / Llama-3)<br/>• ChromaDB / FAISS Vector Store<br/>• EDA Error Playbooks & PDK Specs"]
    end

    subgraph Storage_Layer ["Persistence & Execution Storage"]
        PG[(PostgreSQL 16+<br/>• Runs, Metrics, Lineage<br/>• Tool Versions, Logs Metadata)]
        VectorDB[(Vector Store<br/>ChromaDB / FAISS)]
        Artifacts[("Raw Artifact Store (FS / S3)<br/>• .v, .sdc, .def, .odb, .rpt<br/>• Raw stdout/stderr logs")]
    end

    subgraph EDA_Tools ["Underlying EDA Toolchain (Linux / Docker)"]
        Yosys["Yosys 0.38+<br/>(Generic / Standard Cell Synthesis)"]
        OpenROAD["OpenROAD v2.0+<br/>(Floorplan, CTS, Global & Detail Route)"]
        PDK["Open-Source PDKs<br/>(SkyWater 130nm / NanGate 45nm)"]
    end

    %% Data and control flows
    Dashboard <-->|REST / WebSockets| API
    API -->|Dispatch Jobs| Orchestrator
    Orchestrator -->|Execute TCL / Scripts| Yosys
    Orchestrator -->|Execute TCL / Scripts| OpenROAD
    Yosys -.->|Reads| PDK
    OpenROAD -.->|Reads| PDK
    Yosys -->|Raw Logs & Netlists| Artifacts
    OpenROAD -->|Raw Logs, Reports, ODB| Artifacts

    Orchestrator -->|Raw Logs| LogParser
    LogParser -->|Metrics & Warnings| PG
    LogParser -->|Signoff Metrics| DatasetMgr

    Orchestrator -->|Synthesized Netlist| FeatureExtractor
    FeatureExtractor -->|Structural Features| DatasetMgr
    DatasetMgr -->|Tabular Datasets| PG
    DatasetMgr -->|Train / Eval| MLEngine

    MLEngine -->|Inference Predictions| API
    LogParser -->|Execution Signatures| AnomalyDet
    AnomalyDet -->|Flagged Anomalies| PG
    AnomalyDet -->|Anomaly Trigger| RAGAssist

    RAGAssist <-->|Query / Retrieve Context| VectorDB
    RAGAssist -->|Actionable Debug Fixes| API
    PG <-->|Query State / Reports| API
```

---

## 2. Repository Directory Structure

```text
eda-genius/
├── .github/
│   └── workflows/
│       ├── lint_and_test.yml          # CI pipeline: ruff, mypy, pytest
│       └── docker_build.yml           # Container build & smoke tests
├── configs/
│   ├── base_config.yaml               # Default system, paths, and DB configs
│   ├── eda_toolchains.yaml            # Tool paths, PDK configurations, default flags
│   └── ml_experiments.yaml            # Hyperparameters, feature subsets, target definitions
├── docker/
│   ├── Dockerfile.eda                 # Ubuntu 22.04 + Yosys + OpenROAD + Python 3.11
│   ├── Dockerfile.api                 # Lightweight container for FastAPI + ML inference
│   └── docker-compose.yml             # PostgreSQL, ChromaDB, Ollama, API orchestration
├── docs/
│   ├── architecture.md                # System architectural blueprint (this file)
│   ├── eda_toolchain_setup.md         # Yosys & OpenROAD installation & PDK setup
│   └── api_spec.md                    # REST API OpenAPI schema and usage
├── scripts/
│   ├── setup_env.sh                   # Environment provisioning script for Linux/WSL2
│   ├── download_pdk.sh                # Fetch SkyWater 130nm / NanGate 45nm PDKs
│   ├── seed_database.py               # Preload reference designs and historical benchmarks
│   └── run_regression.py              # CLI batch runner for regression sweeps
├── src/
│   ├── __init__.py
│   ├── common/                        # Shared utilities, schemas, and base exceptions
│   │   ├── __init__.py
│   │   ├── config.py                  # Pydantic Settings implementation
│   │   ├── exceptions.py              # Strongly-typed domain error hierarchy
│   │   ├── logger.py                  # Structured Loguru / JSON logger with run_id
│   │   └── types.py                   # Common enums (ToolType, StageStatus, MetricKey)
│   ├── orchestration/                 # Module 1: EDA Orchestration Engine
│   │   ├── __init__.py
│   │   ├── base.py                    # ToolRunner protocol & pipeline orchestrator
│   │   ├── yosys_runner.py            # Yosys script generation, process execution, timeout
│   │   ├── openroad_runner.py         # OpenROAD TCL generation, step execution (FP, CTS, Route)
│   │   └── artifact_manager.py        # Workdir sandboxing, checksums, raw artifact indexing
│   ├── feature_extraction/            # Module 2: RTL & Netlist Feature Extractor
│   │   ├── __init__.py
│   │   ├── base.py                    # FeatureExtractor interface
│   │   ├── rtl_parser.py              # AST traversal, module IO, operator & reg counts
│   │   ├── netlist_graph.py           # Gate-level hypergraph: cell types, fanout, depth
│   │   └── interconnect_heuristics.py # Rent's rule, estimated wirelength heuristics
│   ├── dataset_manager/               # Module 3: Experiment Dataset Manager
│   │   ├── __init__.py
│   │   ├── base.py                    # DatasetManager interface
│   │   ├── schema.py                  # Parquet dataset schemas & validation
│   │   ├── exporter.py                # Train/test split generator & tabular dataset exporter
│   │   └── lineage.py                 # Git commit, tool version, PDK hash provenance
│   ├── ml_engine/                     # Module 4: ML Prediction Engine
│   │   ├── __init__.py
│   │   ├── base.py                    # ModelTrainer & ModelPredictor protocols
│   │   ├── models/                    # XGBoost, LightGBM, Random Forest wrappers
│   │   │   ├── timing_regressor.py    # Predict WNS/TNS from pre-layout features
│   │   │   ├── power_regressor.py     # Predict dynamic/leakage power
│   │   │   └── wirelength_regressor.py# Predict post-routing wirelength & area
│   │   ├── evaluation.py              # RMSE, MAE, R², MAPE, cross-validation metrics
│   │   └── interpretability.py        # SHAP feature importance & impact analysis
│   ├── log_intelligence/              # Module 5: EDA Log Intelligence Engine
│   │   ├── __init__.py
│   │   ├── base.py                    # LogParser protocol
│   │   ├── yosys_parser.py            # Yosys stdout parser (cell counts, warnings, area)
│   │   ├── openroad_parser.py         # OpenROAD/OpenSTA timing, power, routing parsers
│   │   └── provenance.py              # Exact line number & byte offset extractor
│   ├── anomaly_detection/             # Module 6: Anomaly Detection Engine
│   │   ├── __init__.py
│   │   ├── base.py                    # AnomalyDetector interface
│   │   ├── rules.py                   # Rule-based guards (GRC overflow, negative slack drops)
│   │   └── statistical.py             # IsolationForest & Z-score distribution anomaly check
│   ├── rag_assistant/                 # Module 7: RAG Diagnostic Assistant
│   │   ├── __init__.py
│   │   ├── base.py                    # DiagnosticAssistant protocol
│   │   ├── vector_store.py            # ChromaDB / FAISS index manager
│   │   ├── document_loader.py         # EDA manual, PDK techfile, and known error ingestor
│   │   ├── embeddings.py              # SentenceTransformer embedding wrapper
│   │   └── agent.py                   # Ollama LLM diagnostic prompt engine
│   ├── api/                           # Module 8: FastAPI Backend
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI application entrypoint
│   │   ├── dependencies.py            # DB session, auth, and engine dependency injection
│   │   ├── routers/
│   │   │   ├── runs.py                # Trigger, monitor, and query runs
│   │   │   ├── predictions.py         # Pre-layout metric estimation endpoints
│   │   │   ├── diagnostics.py         # Failure triage & RAG assistant chat
│   │   │   └── analytics.py           # Pareto data & historical aggregations
│   │   └── schemas/                   # Pydantic request/response schemas
│   └── database/                      # Persistence Layer
│       ├── __init__.py
│       ├── connection.py              # SQLAlchemy async engine & sessionmaker
│       ├── models.py                  # Declarative SQLAlchemy ORM entities
│       └── migrations/                # Alembic migration scripts
├── benchmarks/                        # Real open-source RTL testbenches (verilog)
│   ├── alu/                           # Simple combinational/sequential ALU
│   ├── aes128/                        # Medium-complexity crypto core
│   ├── picorv32/                      # RISC-V 32-bit core
│   └── ibex/                          # 2-stage in-order 32-bit RISC-V core
├── tests/
│   ├── conftest.py                    # Pytest fixtures, mock log files, temp workdirs
│   ├── unit/                          # Unit tests for parsers, extractors, ML logic
│   ├── integration/                   # Integration between DB, parsers, and API
│   └── e2e/                           # End-to-end pipeline execution with real tools
├── pyproject.toml                     # Poetry/Pdm/Pip toolchain dependencies
├── Makefile                           # Developer ergonomics (make test, make lint, make run)
└── README.md                          # Repository overview and quickstart
```

---

## 3. Database Schema Proposal (PostgreSQL)

The database schema is designed with strict relational constraints, foreign keys, timestamps, audit metadata, and `JSONB` flexibility for unstructured EDA metrics and tool telemetry without sacrificing query performance.

```mermaid
erDiagram
    DESIGN ||--o{ RUN : has
    RUN ||--|{ RUN_STAGE : executes
    RUN ||--o{ STAGE_METRIC : yields
    RUN ||--o{ RUN_ANOMALY : detects
    RUN ||--o{ DIAGNOSTIC_SESSION : triggers
    MODEL_REGISTRY ||--o{ MODEL_INFERENCE : logs

    DESIGN {
        uuid id PK
        string name UK
        string rtl_top_module
        string source_repo_url
        string commit_hash
        timestamp created_at
    }

    RUN {
        uuid id PK
        uuid design_id FK
        string status
        string target_pdk
        float clock_period_ns
        jsonb tool_versions
        jsonb run_config
        string workdir_path
        timestamp started_at
        timestamp completed_at
        float total_wall_time_s
    }

    RUN_STAGE {
        uuid id PK
        uuid run_id FK
        string stage_name
        int stage_order
        string tool_name
        string status
        int exit_code
        string raw_log_path
        string output_artifact_path
        float runtime_s
        float peak_memory_mb
        timestamp started_at
        timestamp completed_at
    }

    STAGE_METRIC {
        uuid id PK
        uuid run_id FK
        uuid run_stage_id FK
        string metric_category
        string metric_name
        float float_value
        string string_value
        jsonb metadata_json
        int log_line_number
        int log_byte_offset
        timestamp recorded_at
    }

    RUN_ANOMALY {
        uuid id PK
        uuid run_id FK
        uuid run_stage_id FK
        string severity
        string anomaly_type
        string message
        jsonb diagnostic_payload
        timestamp detected_at
    }

    DIAGNOSTIC_SESSION {
        uuid id PK
        uuid run_id FK
        string prompt
        text retrieved_context
        text llm_response
        string model_name
        float latency_s
        timestamp created_at
    }

    MODEL_REGISTRY {
        uuid id PK
        string model_name UK
        string target_metric
        string algorithm
        jsonb hyperparameters
        float val_r2_score
        float val_rmse
        string artifact_path
        timestamp trained_at
    }

    MODEL_INFERENCE {
        uuid id PK
        uuid model_id FK
        uuid run_id FK
        jsonb input_features
        float predicted_value
        float actual_value
        float absolute_error
        timestamp created_at
    }
```

### PostgreSQL DDL Definitions & Indexes

```sql
-- Core Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enum Definitions
CREATE TYPE run_status_enum AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'ABORTED');
CREATE TYPE stage_name_enum AS ENUM ('SYNTHESIS', 'FLOORPLAN', 'PLACEMENT', 'CTS', 'ROUTING', 'SIGNOFF');
CREATE TYPE anomaly_severity_enum AS ENUM ('INFO', 'WARNING', 'CRITICAL', 'FATAL');

-- 1. Designs Table
CREATE TABLE designs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL UNIQUE,
    rtl_top_module VARCHAR(128) NOT NULL,
    source_repo_url TEXT,
    commit_hash VARCHAR(64),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Runs Table
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    design_id UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    status run_status_enum NOT NULL DEFAULT 'PENDING',
    target_pdk VARCHAR(64) NOT NULL, -- e.g. 'sky130hd', 'nangate45'
    clock_period_ns NUMERIC(8, 4) NOT NULL,
    tool_versions JSONB NOT NULL,    -- {'yosys': '0.38+10', 'openroad': '2.0-1340'}
    run_config JSONB NOT NULL,       -- complete parameters, target density, max fanout
    workdir_path TEXT NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    total_wall_time_s NUMERIC(10, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_runs_design_id ON runs(design_id);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_target_pdk ON runs(target_pdk);
CREATE INDEX idx_runs_created_at ON runs(created_at DESC);

-- 3. Run Stages Table
CREATE TABLE run_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    stage_name stage_name_enum NOT NULL,
    stage_order SMALLINT NOT NULL,
    tool_name VARCHAR(64) NOT NULL,  -- 'yosys', 'openroad'
    status run_status_enum NOT NULL DEFAULT 'PENDING',
    exit_code INTEGER,
    raw_log_path TEXT,
    output_artifact_path TEXT,       -- path to .v, .def, or .odb checkpoint
    runtime_s NUMERIC(10, 2),
    peak_memory_mb NUMERIC(10, 2),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_run_stage_order UNIQUE(run_id, stage_order)
);
CREATE INDEX idx_run_stages_run_id ON run_stages(run_id);

-- 4. Stage Metrics Table (Atomic & Parsed Signoff Values)
CREATE TABLE stage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    run_stage_id UUID NOT NULL REFERENCES run_stages(id) ON DELETE CASCADE,
    metric_category VARCHAR(64) NOT NULL, -- 'TIMING', 'AREA', 'POWER', 'CONGESTION', 'CELL_COUNT'
    metric_name VARCHAR(128) NOT NULL,    -- 'wns', 'tns', 'total_cells', 'dynamic_power_mw', 'die_area_um2'
    float_value DOUBLE PRECISION,
    string_value TEXT,
    metadata_json JSONB,
    log_line_number INTEGER,
    log_byte_offset BIGINT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_stage_metrics_query ON stage_metrics(run_id, metric_name);
CREATE INDEX idx_stage_metrics_category ON stage_metrics(metric_category);

-- 5. Run Anomalies Table
CREATE TABLE run_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    run_stage_id UUID REFERENCES run_stages(id) ON DELETE SET NULL,
    severity anomaly_severity_enum NOT NULL,
    anomaly_type VARCHAR(128) NOT NULL, -- 'GRC_CONGESTION_OVERFLOW', 'TIMING_HOLD_DEVIATION', 'UNCONSTRAINED_PINS'
    message TEXT NOT NULL,
    diagnostic_payload JSONB,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_anomalies_run_id ON run_anomalies(run_id);
CREATE INDEX idx_anomalies_severity ON run_anomalies(severity);

-- 6. Diagnostic Sessions (RAG Assistant Audit Trail)
CREATE TABLE diagnostic_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    retrieved_context TEXT NOT NULL,
    llm_response TEXT NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    latency_s NUMERIC(6, 3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_diagnostic_sessions_run ON diagnostic_sessions(run_id);

-- 7. ML Model Registry
CREATE TABLE model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(128) NOT NULL UNIQUE,
    target_metric VARCHAR(128) NOT NULL, -- 'post_route_wns', 'total_power_mw', 'core_area'
    algorithm VARCHAR(64) NOT NULL,      -- 'XGBoost', 'LightGBM', 'RandomForest'
    hyperparameters JSONB NOT NULL,
    val_r2_score DOUBLE PRECISION NOT NULL,
    val_rmse DOUBLE PRECISION NOT NULL,
    artifact_path TEXT NOT NULL,
    trained_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. ML Inferences Table
CREATE TABLE model_inferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    input_features JSONB NOT NULL,
    predicted_value DOUBLE PRECISION NOT NULL,
    actual_value DOUBLE PRECISION,
    absolute_error DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_inferences_model_run ON model_inferences(model_id, run_id);
```

---

## 4. Module Interface Definitions (Code Contracts)

All modules communicate strictly through Python Protocol and Pydantic v2 data models. No module directly invokes another module's internal implementation details.

### A. Shared Types & Common Domain Models

```python
# src/common/types.py
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class ToolType(str, Enum):
    YOSYS = "yosys"
    OPENROAD = "openroad"

class StageName(str, Enum):
    SYNTHESIS = "SYNTHESIS"
    FLOORPLAN = "FLOORPLAN"
    PLACEMENT = "PLACEMENT"
    CTS = "CTS"
    ROUTING = "ROUTING"
    SIGNOFF = "SIGNOFF"

class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"

class ExecutionResult(BaseModel):
    tool: ToolType
    stage: StageName
    exit_code: int
    runtime_s: float
    peak_memory_mb: float
    stdout_path: str
    stderr_path: str
    artifact_paths: Dict[str, str] = Field(default_factory=dict)
    success: bool
```

### B. Module 1: EDA Orchestration Engine

```python
# src/orchestration/base.py
from typing import Protocol, Dict, Any, List
from pathlib import Path
from src.common.types import ExecutionResult, StageName, RunStatus

class ToolRunner(Protocol):
    """Protocol for executing specific EDA tools."""
    tool_name: str

    def generate_script(self, template_params: Dict[str, Any], output_path: Path) -> Path:
        """Render and persist tool-specific TCL/command scripts."""
        ...

    def execute(self, script_path: Path, workdir: Path, timeout_s: int = 1800) -> ExecutionResult:
        """Run tool sub-process with resource tracking and stdout/stderr capture."""
        ...

class EDAOrchestrationEngine(Protocol):
    """Protocol for the end-to-end flow manager."""
    def initialize_run(self, run_id: str, design_name: str, config: Dict[str, Any]) -> Path:
        """Create sandboxed working directory and log files."""
        ...

    def execute_stage(self, run_id: str, stage: StageName, config: Dict[str, Any]) -> ExecutionResult:
        """Execute a single pipeline stage."""
        ...

    def run_full_flow(self, run_id: str, design_files: List[Path], config: Dict[str, Any]) -> Dict[StageName, ExecutionResult]:
        """Execute synthesis through physical design signoff."""
        ...
```

### C. Module 2: RTL & Netlist Feature Extractor

```python
# src/feature_extraction/base.py
from typing import Protocol, Dict, Any
from pathlib import Path
from pydantic import BaseModel

class NetlistFeatures(BaseModel):
    num_cells: int
    num_combinational_cells: int
    num_sequential_cells: int
    combinational_to_sequential_ratio: float
    num_nets: int
    num_pins: int
    max_fanout: int
    avg_fanout: float
    logic_depth_max: int
    logic_depth_avg: float
    cell_type_histogram: Dict[str, int]
    rents_exponent_estimate: float
    estimated_hpwl: Optional[float] = None

class FeatureExtractor(Protocol):
    """Protocol for structural RTL and Gate-Level netlist feature extraction."""
    def extract_from_rtl(self, rtl_path: Path, top_module: str) -> Dict[str, Any]:
        """Syntactic/AST feature extraction before synthesis."""
        ...

    def extract_from_gate_netlist(self, netlist_v_path: Path) -> NetlistFeatures:
        """Extract graph-theoretic and structural metrics from post-synthesis Verilog."""
        ...
```

### D. Module 3: Experiment Dataset Manager

```python
# src/dataset_manager/base.py
from typing import Protocol, List, Optional
import pandas as pd
from pathlib import Path
from pydantic import BaseModel

class DatasetPartition(BaseModel):
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    feature_columns: List[str]
    target_columns: List[str]

class ExperimentDatasetManager(Protocol):
    """Protocol for preparing ML datasets from EDA runs and historical signoff metrics."""
    def assemble_tabular_record(self, run_id: str) -> Dict[str, Any]:
        """Combine netlist features with actual signoff metrics (WNS, power, area)."""
        ...

    def export_parquet(self, output_path: Path, filter_tags: Optional[Dict[str, Any]] = None) -> Path:
        """Export dataset to Apache Parquet format."""
        ...

    def generate_train_test_split(self, dataset_path: Path, test_ratio: float = 0.2) -> DatasetPartition:
        """Generate stratified or design-independent train/test partitions."""
        ...
```

### E. Module 4: ML Prediction Engine

```python
# src/ml_engine/base.py
from typing import Protocol, Dict, Any, List
import pandas as pd
from pathlib import Path
from pydantic import BaseModel

class ModelPerformance(BaseModel):
    model_name: str
    target_metric: str
    r2: float
    rmse: float
    mae: float
    mape: float

class MLPredictionEngine(Protocol):
    """Protocol for surrogate model training, inference, and SHAP interpretability."""
    def train(self, target_metric: str, train_df: pd.DataFrame, feature_cols: List[str]) -> ModelPerformance:
        """Train surrogate regressor (e.g. XGBoost) to predict downstream metric."""
        ...

    def predict(self, model_name: str, features: Dict[str, Any]) -> float:
        """Predict physical design metric (WNS, wirelength, power) from netlist features."""
        ...

    def explain(self, model_name: str, features: Dict[str, Any]) -> Dict[str, float]:
        """Return SHAP feature contribution values for the prediction."""
        ...

    def save_model(self, model_name: str, target_dir: Path) -> Path:
        """Serialize model artifact to disk."""
        ...
```

### F. Module 5: EDA Log Intelligence Engine

```python
# src/log_intelligence/base.py
from typing import Protocol, List
from pathlib import Path
from pydantic import BaseModel

class ParsedLogEntry(BaseModel):
    category: str
    metric_name: str
    value: float | str
    line_number: int
    byte_offset: int
    raw_snippet: str

class EDALogIntelligenceEngine(Protocol):
    """Protocol for structured extraction from raw EDA execution logs."""
    def parse_yosys_log(self, log_path: Path) -> List[ParsedLogEntry]:
        """Parse cell allocations, runtime, memory, and synthesis warnings."""
        ...

    def parse_openroad_log(self, log_path: Path) -> List[ParsedLogEntry]:
        """Parse timing (WNS/TNS), core utilization, wirelength, and DRC/routing metrics."""
        ...

    def extract_critical_errors(self, log_path: Path) -> List[str]:
        """Identify fatal and convergence-halting error strings with context."""
        ...
```

### G. Module 6: Anomaly Detection Engine

```python
# src/anomaly_detection/base.py
from typing import Protocol, List, Dict, Any
from pydantic import BaseModel
from src.common.types import StageName

class AnomalyReport(BaseModel):
    severity: str
    anomaly_type: str
    stage: StageName
    message: str
    metric_deviations: Dict[str, Dict[str, float]] # e.g. {"wns": {"expected": 0.0, "actual": -3.42}}

class AnomalyDetectionEngine(Protocol):
    """Protocol for identifying execution divergence, runtime spikes, and routing congestion."""
    def inspect_stage(self, stage: StageName, current_metrics: Dict[str, Any]) -> List[AnomalyReport]:
        """Evaluate deterministic rule-based guards."""
        ...

    def evaluate_statistical_outliers(self, metric_name: str, current_value: float) -> Optional[AnomalyReport]:
        """Evaluate IsolationForest / Z-score deviations against historical distributions."""
        ...
```

### H. Module 7: RAG-based Diagnostic Assistant

```python
# src/rag_assistant/base.py
from typing import Protocol, List, Dict, Any
from pydantic import BaseModel

class DiagnosticQuery(BaseModel):
    run_id: str
    failed_stage: str
    error_summary: str
    recent_logs: str
    metrics: Dict[str, Any]

class DiagnosticResponse(BaseModel):
    root_cause_hypothesis: str
    remediation_steps: List[str]
    retrieved_manual_references: List[str]
    confidence_score: float

class RAGDiagnosticAssistant(Protocol):
    """Protocol for LLM diagnostic triage and playbook recommendations."""
    def index_documents(self, document_paths: List[str]) -> int:
        """Ingest EDA tool user guides, SDC syntax guides, and PDK rules."""
        ...

    def diagnose_failure(self, query: DiagnosticQuery) -> DiagnosticResponse:
        """Generate root-cause explanation and fix suggestions using local Ollama model."""
        ...
```

### I. Module 8: FastAPI Backend

```python
# src/api/schemas/runs.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from src.common.types import RunStatus

class RunSubmitRequest(BaseModel):
    design_name: str
    target_pdk: str = Field(default="sky130hd")
    clock_period_ns: float = Field(gt=0.0)
    parameters: Dict[str, Any] = Field(default_factory=dict)

class RunStatusResponse(BaseModel):
    run_id: str
    design_name: str
    status: RunStatus
    completed_stages: List[str]
    current_stage: Optional[str]
    metrics_summary: Dict[str, Any]
    error_message: Optional[str] = None
```

---

## 5. Configuration Management Specification

Configuration is managed using **Pydantic Settings v2**, supporting hierarchical configuration:
1. Default YAML files (`configs/base_config.yaml`, `configs/eda_toolchains.yaml`)
2. Environment variables prefixed with `EDAGENIUS_` (e.g. `EDAGENIUS_DATABASE_URL`)
3. Command-line argument overrides.

### Configuration Schema Definition

```python
# src/common/config.py
from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional

class EDAConfig(BaseSettings):
    yosys_binary: str = "/usr/bin/yosys"
    openroad_binary: str = "/usr/bin/openroad"
    default_pdk_path: Path = Path("/opt/pdks/sky130A")
    default_timeout_s: int = 3600
    workdir_root: Path = Path("./artifacts/runs")

class DatabaseConfig(BaseSettings):
    url: PostgresDsn = Field(default="postgresql+asyncpg://eda_user:eda_pass@localhost:5432/eda_genius")
    echo_sql: bool = False
    pool_size: int = 10
    max_overflow: int = 20

class RAGConfig(BaseSettings):
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_persist_dir: Path = Path("./artifacts/chroma_db")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EDAGENIUS_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore"
    )
    environment: str = "development"
    debug: bool = False
    eda: EDAConfig = Field(default_factory=EDAConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)

settings = Settings()
```

---

## 6. Structured Logging & Error Handling Strategy

### A. Logging Strategy
- Utilizes structured JSON logging via `Loguru` or standard logging handlers.
- Injects request/run context into all log lines:
  - `run_id`: UUID of the active run.
  - `stage`: Current stage (`SYNTHESIS`, `ROUTING`).
  - `tool`: Executed binary name.
- Emits real-time log events to disk (`artifacts/runs/{run_id}/run.log`) and broadcasts through FastAPI WebSockets for live frontend streaming.

### B. Error Handling Hierarchy

```text
EDAGeniusException (Base)
├── ConfigurationError (Invalid parameters, missing PDK, missing tool binary)
├── ToolExecutionError (Process non-zero exit, timeout, segmentation fault)
│   ├── SynthesisConvergenceError (Yosys syntax error, unmapped cells)
│   ├── PhysicalDesignError (OpenROAD core violation, DRC failure)
│   └── ToolTimeoutError (Execution exceeded configured walltime)
├── LogParsingError (Regex failure, malformed tool report)
├── DatasetIntegrityError (Missing features, corrupted parquet table)
├── ModelInferenceError (Model artifact not found, dimension mismatch)
└── DiagnosticAssistantError (Ollama unavailable, context length overflow)
```

Each exception explicitly stores:
1. `exit_code`: Numeric status code from tool.
2. `stderr_tail`: Last 50 lines of execution error output.
3. `command`: Exact command line invocation for direct reproducibility.

---

## 7. Testing Strategy: Unit, Integration & E2E

### A. Unit Tests (`tests/unit/`)
- **Log Intelligence:** Test regular expressions and state machine against static, recorded real-world Yosys logs and OpenROAD/OpenSTA timing reports.
- **Feature Extractor:** Test AST and netlist graph analyzers on verified Verilog snippets (ALU, counter).
- **ML Engine:** Validate cross-validation split generation, evaluation metrics calculation, and serialization round-trip without requiring real EDA tools.
- **Anomaly Detection:** Verify threshold checks and Isolation Forest behavior with synthetic metric distributions.

### B. Integration Tests (`tests/integration/`)
- **Database Layer:** Execute migrations (Alembic) on a live test PostgreSQL container; test async insert, update, cascade delete, and JSONB queries.
- **API Endpoints:** Use FastAPI `TestClient` to submit jobs, verify status transitions, and retrieve diagnostic responses.
- **Vector Retrieval:** Ingest reference documentation chunks into ChromaDB and verify recall on test queries.

### C. End-to-End (E2E) Tests (`tests/e2e/`)
- Execute complete flow on real open-source benchmark circuits (`benchmarks/alu`):
  1. Synthesis via Yosys.
  2. Parse stdout/stderr and store cell counts in DB.
  3. Extract netlist graph features.
  4. Run OpenROAD floorplan -> placement -> CTS -> routing.
  5. Parse signoff timing report (OpenSTA) for WNS/TNS.
  6. Verify all database records, log provenance offsets, and generated checkpoints.

---

## 8. Installation & Environment Setup Instructions

### Prerequisites
- **Operating System:** Linux (Ubuntu 22.04 LTS recommended) or Windows Subsystem for Linux (WSL2).
- **Runtime:** Python 3.11+, Git, Docker & Docker Compose.
- **Hardware:** Minimum 4 vCPUs, 16 GB RAM (32 GB recommended for full OpenROAD routing on larger designs).

### 1. Host Toolchain Installation (Ubuntu 22.04 / WSL2)

```bash
# Update and install system dependencies
sudo apt-get update && sudo apt-get install -y \
    build-essential cmake git curl python3.11 python3.11-venv python3-pip \
    tcl-dev tk-dev libffi-dev libreadline-dev bison flex libboost-all-dev

# Install Yosys
sudo apt-get install -y yosys

# Install OpenROAD (using prebuilt binary or official container)
# Recommended via official OpenROAD binary package:
curl -s https://api.github.com/repos/The-OpenROAD-Project/OpenROAD/releases/latest \
  | grep "browser_download_url.*ubuntu22.04.*deb" \
  | cut -d : -f 2,3 | tr -d \" | wget -qi -
sudo dpkg -i openroad*.deb || sudo apt-get install -f -y
```

### 2. Python Environment Setup

```bash
# Create and activate Python 3.11 virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install core dependencies
pip install --upgrade pip setuptools wheel
pip install fastapi uvicorn[standard] sqlalchemy asyncpg psycopg2-binary alembic \
    pydantic pydantic-settings numpy pandas scikit-learn xgboost lightgbm \
    sentence-transformers chromadb loguru pyyaml click
```

### 3. Local LLM Service (Ollama)

```bash
# Install and run Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models for code and diagnostic reasoning
ollama pull qwen2.5-coder:7b
ollama pull llama3:8b
```

### 4. Containerized Infrastructure via Docker Compose

```bash
# Start PostgreSQL, ChromaDB, and Adminer
docker compose -f docker/docker-compose.yml up -d
```

---

## 9. Development Milestones & Phased Roadmap

| Milestone | Scope & Deliverables | Exit Criteria |
| :--- | :--- | :--- |
| **Phase 0: Architecture & Foundation** *(Current)* | Architectural design, database schema, module protocols, repo scaffold, configuration, environment setup. | User approval of foundation design. |
| **Phase 1: EDA Orchestration & Log Intelligence** | Yosys/OpenROAD runners, process isolation, real-time log capturing, regex/state-machine parsers for timing, area, power, and provenance offset tracking. | End-to-end execution of `benchmarks/alu` generating real `.rpt` and populating PostgreSQL. |
| **Phase 2: Feature Extraction & Dataset Manager** | AST and gate-level netlist graph feature extractor (cell ratios, fanout, Rent's rule). Experiment dataset assembler and Parquet exporter. | Automated generation of verified tabular dataset from historical runs. |
| **Phase 3: ML Predictive Optimization Engine** | Surrogate timing (WNS/TNS) and power regressors (XGBoost/LightGBM). Evaluation harness, SHAP interpretability module, and model persistence. | R² > 0.85 on test benchmarks; automated feature importance ranking. |
| **Phase 4: Anomaly Detection & RAG Diagnostic Assistant** | Real-time and statistical anomaly detectors. ChromaDB vector indexing of EDA manuals/PDK specs. Ollama-powered diagnostic triage agent. | Accurate triage and remediation suggestions for simulated synthesis/routing failures. |
| **Phase 5: FastAPI Backend & Experiment Analytics Dashboard** | REST API gateway, WebSocket log streaming, React frontend with run timeline, Pareto frontier visualizer, and RAG chat. | Fully interactive portfolio demonstration platform ready for deployment. |
