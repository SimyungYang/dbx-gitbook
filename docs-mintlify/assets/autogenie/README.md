# AutoGenie

A unified Databricks Apps platform for creating and enhancing Genie Spaces using AI-powered workflows.

## Overview

AutoGenie combines two powerful workflows into a single tabbed application:

- **Lamp** (Create): Generate new Genie Spaces from natural language requirements documents
- **Enhancer** (Improve): Optimize existing Genie Spaces through benchmark-driven iterative enhancement

Built as a Databricks App with a FastAPI backend and Next.js frontend, AutoGenie leverages Databricks Foundation Models for intelligent configuration generation and optimization.

## Features

### Lamp Workflow - Create New Genie Spaces

Transform requirements documents into fully configured Genie Spaces:

| Step | Description |
|------|-------------|
| **Upload & Parse** | Upload PDF/Markdown requirements, extract metrics and business logic using LLM |
| **Generate** | AI generates complete Genie Space configuration (tables, joins, instructions) |
| **Validate** | Verify table references against Unity Catalog, fix mismatches interactively |
| **Benchmark** | Extract and validate benchmark SQL queries from requirements |
| **Deploy** | Deploy the configured Genie Space to Databricks workspace |

### Enhancer Workflow - Improve Existing Spaces

Iteratively optimize Genie Space performance using benchmarks:

| Step | Description |
|------|-------------|
| **Configure** | Select target Genie Space, SQL warehouse, and upload benchmarks |
| **Score** | Run benchmarks against the space, measure pass/fail rates |
| **Plan** | AI analyzes failures and proposes fixes (instructions, sample queries, joins) |
| **Apply** | Apply approved fixes to the Genie Space configuration |

**Enhancement Modes:**
- **Manual Mode**: Step through Score → Plan → Apply with approval at each stage
- **Auto-Loop Mode**: Automatically iterate until target score is reached or max iterations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  ┌─────────────────┐              ┌─────────────────────────┐   │
│  │   Lamp Tab      │              │    Enhancer Tab         │   │
│  │  - ParseStep    │              │  - ConfigureStep        │   │
│  │  - GenerateStep │              │  - ScoreStep            │   │
│  │  - ValidateStep │              │  - PlanStep             │   │
│  │  - BenchmarkStep│              │  - ApplyStep            │   │
│  │  - DeployStep   │              │  - AutoLoopStep         │   │
│  └─────────────────┘              └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   /api/lamp │  │/api/enhancer│  │     Shared Services     │  │
│  │  - /parse   │  │ - /jobs/*   │  │  - SessionStore (SQLite)│  │
│  │  - /generate│  │ - /sessions │  │  - JobManager           │  │
│  │  - /validate│  │ - /workspace│  │  - FileStorage          │  │
│  │  - /deploy  │  │ - /iterations│  │  - Auth Middleware      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Core Modules                                  │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐   │
│  │       genie/            │  │       enhancer/             │   │
│  │  - parsing/ (PDF, MD)   │  │  - scoring/ (benchmarks)    │   │
│  │  - pipeline/ (gen/val)  │  │  - enhancement/ (fixes)     │   │
│  │  - api/ (Genie client)  │  │  - api/ (Space operations)  │   │
│  │  - llm/ (Databricks)    │  │  - llm/ (analysis)          │   │
│  │  - validation/          │  │  - utils/                   │   │
│  └─────────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Databricks Platform                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐  │
│  │Unity Catalog│  │Genie Spaces│  │SQL Warehouse│  │Foundation │  │
│  │  (Tables)   │  │   (API)    │  │  (Compute)  │  │  Models   │  │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - Async web framework
- **SQLite** - Session and job persistence
- **Databricks SDK** - Workspace operations
- **PyJWT** - Token handling

### Frontend
- **Next.js 14** - React framework (static export)
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **React Markdown** - Markdown rendering

### AI/ML
- **Databricks Foundation Models** - LLM for generation and analysis
- **databricks-gpt-5-2** - Default model endpoint

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Databricks CLI configured
- Access to a Databricks workspace

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AutoGenie
   ```

2. **Create Python virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

5. **Configure environment**
   ```bash
   # Create .env file with required variables
   cat > .env << EOF
   DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
   DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
   EOF
   ```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABRICKS_HOST` | Databricks workspace URL | Yes |
| `DATABRICKS_HTTP_PATH` | SQL Warehouse HTTP path | Yes |
| `DATABRICKS_SERVICE_TOKEN` | Service account PAT (production) | No |
| `DATABRICKS_CLIENT_ID` | OAuth client ID (Databricks Apps) | Auto |
| `DATABRICKS_CLIENT_SECRET` | OAuth client secret (Databricks Apps) | Auto |
| `FRONTEND_EXPORT_DIR` | Frontend static files path | No |

### Authentication Modes

AutoGenie supports multiple authentication modes:

1. **User Token (Production)**: `X-Forwarded-Access-Token` header injected by Databricks Apps gateway
2. **Service Principal**: OAuth M2M for backend-only operations
3. **Databricks CLI (Local)**: Automatic token from `databricks auth token`

### Secrets (Databricks Apps)

Create a secrets scope named `autogenie`:
```bash
databricks secrets create-scope autogenie
databricks secrets put-secret autogenie service-token --string-value "your-pat-token"
```

## Running Locally

### Development Mode

Start backend and frontend separately for hot-reloading:

```bash
# Terminal 1: Backend
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Access the application at `http://localhost:3000`

### Production Build

Build frontend and run as unified app:

```bash
# Build frontend static export
cd frontend
npm run build
cd ..

# Run backend serving static files
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Access at `http://localhost:8000`

## Deployment to Databricks Apps

1. **Build frontend**
   ```bash
   cd frontend && npm run build && cd ..
   ```

2. **Deploy using Databricks CLI**
   ```bash
   databricks apps deploy . --name autogenie
   ```

3. **Configure app permissions** in Databricks workspace

## API Reference

### Shared Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/sessions` | List all sessions |
| POST | `/api/sessions` | Create new session |
| GET | `/api/sessions/{id}` | Get session details |
| PUT | `/api/sessions/{id}` | Update session name |
| DELETE | `/api/sessions/{id}` | Delete session |
| GET | `/api/jobs/{id}` | Get job status |
| POST | `/api/jobs/{id}/cancel` | Cancel running job |

### Lamp Endpoints (`/api/lamp`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/parse` | Parse uploaded requirements |
| POST | `/generate` | Generate Genie Space config |
| POST | `/validate` | Validate against Unity Catalog |
| POST | `/validate/fix` | Apply fixes and re-validate |
| POST | `/deploy` | Deploy to Databricks |
| POST | `/benchmark/validate` | Validate benchmark queries |
| GET | `/files/{session}/{file}` | Get file content |
| GET | `/download/config/{session}` | Download config JSON |

### Enhancer Endpoints (`/api/enhancer`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/workspace/warehouses` | List SQL warehouses |
| GET | `/workspace/spaces` | List Genie Spaces |
| POST | `/jobs/score` | Start scoring job |
| POST | `/jobs/plan` | Start planning job |
| POST | `/jobs/apply` | Apply fixes |
| POST | `/sessions/{id}/auto-loop` | Start auto-loop |
| GET | `/iterations/{id}` | Get iteration status |
| POST | `/iterations/{id}/approve` | Approve and apply fixes |
| POST | `/sessions/{id}/upload` | Upload benchmark file |
| GET | `/benchmarks/template` | Get benchmark template |

## Database Schema

AutoGenie uses SQLite for persistence with the following tables:

### `autogenie_sessions`
| Column | Type | Description |
|--------|------|-------------|
| session_id | TEXT PK | Unique session identifier |
| user_id | TEXT | User who created the session |
| name | TEXT | Session display name |
| workflow_type | TEXT | 'lamp' or 'enhancer' |
| target_score | REAL | Target benchmark score (enhancer) |
| max_iterations | INT | Max enhancement iterations |
| loop_status | TEXT | Auto-loop status |
| deployed_space_id | TEXT | Deployed Genie Space ID |

### `autogenie_jobs`
| Column | Type | Description |
|--------|------|-------------|
| job_id | TEXT PK | Unique job identifier |
| session_id | TEXT FK | Parent session |
| type | TEXT | Job type (parse, generate, score, etc.) |
| status | TEXT | pending, running, completed, failed |
| inputs | JSON | Job input parameters |
| result | JSON | Job output/result |
| progress | JSON | Progress events |

### `autogenie_iterations`
| Column | Type | Description |
|--------|------|-------------|
| iteration_id | TEXT PK | Unique iteration identifier |
| session_id | TEXT FK | Parent session |
| iteration_number | INT | Iteration sequence number |
| score_before | REAL | Score at start |
| score_after | REAL | Score after applying fixes |
| fixes_proposed | JSON | LLM-proposed fixes |
| fixes_applied | JSON | User-approved fixes |

## Project Structure

```
AutoGenie/
├── app.yaml                    # Databricks Apps configuration
├── databricks.yml              # Databricks Asset Bundle config
├── requirements.txt            # Python dependencies
├── backend/                    # FastAPI server
│   ├── main.py                 # Application entry point
│   ├── middleware/
│   │   └── auth.py             # Authentication (OBO + service principal)
│   ├── services/
│   │   ├── session_store.py    # SQLite session/job persistence
│   │   ├── job_manager.py      # Background job lifecycle
│   │   └── file_storage.py     # Local file handling
│   ├── lamp/
│   │   ├── routes.py           # Lamp API routes (/api/lamp/*)
│   │   ├── tasks.py            # Lamp background tasks
│   │   └── benchmark_validator.py
│   └── enhancer/
│       ├── routes.py           # Enhancer API routes (/api/enhancer/*)
│       ├── tasks.py            # Enhancer background tasks
│       └── iteration_controller.py
├── genie/                      # Lamp core logic
│   ├── parsing/                # PDF/Markdown parsing
│   ├── pipeline/               # Generate/Validate/Deploy
│   ├── api/                    # Genie Space API client
│   ├── llm/                    # Databricks LLM client
│   ├── benchmark/              # Benchmark extraction
│   └── validation/             # Table/SQL validation
├── enhancer/                   # Enhancer core logic
│   ├── scoring/                # Benchmark scoring
│   ├── enhancement/            # Fix generation & application
│   ├── api/                    # Space operations
│   └── utils/                  # Utilities
├── prompts/                    # LLM prompt templates
├── frontend/                   # Next.js 14 (static export)
│   ├── app/
│   │   └── page.tsx            # Main tabbed page
│   ├── components/
│   │   ├── TabNavigation.tsx   # Tab switcher
│   │   ├── SessionSidebar.tsx  # Session list
│   │   ├── Stepper.tsx         # Workflow stepper
│   │   ├── lamp/               # Lamp step components
│   │   └── enhancer/           # Enhancer step components
│   └── lib/
│       └── api-client.ts       # API client
├── docs/                       # Documentation & presentation materials
└── presentations/              # PowerPoint files & build scripts
```

## Benchmark File Format

Benchmarks are JSON files with the following structure:

```json
[
  {
    "question": "What was total revenue last month?",
    "expected_sql": "SELECT SUM(revenue) FROM sales WHERE month = '2024-01'",
    "tags": ["revenue", "monthly"],
    "difficulty": "easy"
  }
]
```

### Required Fields
- `question`: Natural language question
- `expected_sql`: Expected SQL query

### Optional Fields
- `tags`: Categories for grouping
- `difficulty`: easy, medium, hard
- `expected_answer`: Expected result for validation

## Troubleshooting

### Common Issues

**Authentication Errors (401)**
- Ensure Databricks CLI is configured: `databricks auth login`
- Verify `DATABRICKS_HOST` is set correctly
- Check token expiration

**Table Validation Failures**
- Verify Unity Catalog permissions
- Check catalog/schema names in configuration
- Use the validation fixer UI to correct references

**Frontend Not Loading**
- Run `npm run build` in frontend directory
- Check `FRONTEND_EXPORT_DIR` points to `frontend/out`
- Verify static files exist

**Job Stuck in Running**
- Check backend logs for errors
- Jobs may timeout after 10 minutes
- Use cancel endpoint: `POST /api/jobs/{id}/cancel`

## Development

### Running Tests

```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd frontend && npm test
```

### Adding New Enhancement Categories

1. Create prompt template in `prompts/category_*.txt`
2. Register category in `enhancer/enhancement/category_enhancer.py`
3. Add UI controls in `frontend/components/enhancer/PlanStep.tsx`

### Extending Parsing Support

1. Add parser in `genie/parsing/`
2. Register in `genie/pipeline/parser.py`
3. Update file type handling in backend routes

## Additional Documentation

See the `docs/` directory for:
- **PRESENTATION.md** - Talk guide and demo script
- **QUICK_REFERENCE.txt** - Quick start cheat sheet