# Rune-X Modernization Todo List & Target Architecture

**Last Updated:** December 2025  
**Total Tasks:** 47  
**Status:** Planning Phase

---

## Table of Contents

1. [Complete Todo List](#complete-todo-list)
2. [Target Directory Structure](#target-directory-structure)
3. [Architecture Overview](#architecture-overview)
4. [Implementation Phases](#implementation-phases)

---

## Complete Todo List

### Phase 1: Immediate Critical Fixes (1-2 weeks)

#### Split main.py Monolith

- [ ] **phase1-split-main-py**: Extract FastAPI routes to `api/routes.py`
- [ ] **phase1-extract-ocr-service**: Extract OCR orchestration to `core/ocr_service.py`
- [ ] **phase1-extract-translation-service**: Extract translation orchestration to `core/translation_service.py`
- [ ] **phase1-extract-models**: Extract Pydantic models to `models/schemas.py`

**Benefits:** Maintainable, testable, modular architecture

#### Fix TypeScript Build Errors

- [ ] **phase1-fix-typescript-errors**: Remove `ignoreBuildErrors: true` from `next.config.ts`
- [ ] **phase1-enable-strict-types**: Enable `'noImplicitAny': true` in `tsconfig.json`
- [ ] **phase1-fix-all-ts-errors**: Fix all existing TypeScript errors in frontend codebase

**Benefits:** Prevents runtime bugs, ensures strong type contracts

#### Add Modern Python Dependency Management

- [ ] **phase1-create-pyproject**: Create `pyproject.toml` with dev/prod dependencies
- [ ] **phase1-consolidate-requirements**: Remove scattered `requirements.txt` files
- [ ] **phase1-configure-tools**: Configure black, ruff, and mypy in `pyproject.toml`

**Benefits:** Single source of truth, reproducibility, IDE support

---

### Phase 2: Testing & Quality (Week 2)

#### Python Backend Testing

- [ ] **phase2-move-test-scripts**: Move test scripts from `scripts/` to `tests/` directory
- [ ] **phase2-add-integration-tests**: Add integration tests for API endpoints (`test_api_endpoints.py`)
- [ ] **phase2-add-performance-tests**: Add performance/load tests for OCR pipeline
- [ ] **phase2-configure-pytest-coverage**: Configure pytest with coverage reports (`pytest.ini` or `pyproject.toml`)

#### Frontend Next.js/TypeScript Testing

- [ ] **phase2-install-frontend-testing**: Install Jest and Testing Library dependencies
- [ ] **phase2-frontend-unit-tests**: Add unit tests for React components and utility functions
- [ ] **phase2-frontend-api-tests**: Add API route tests for `/api/process`, `/api/upload`, etc.
- [ ] **phase2-frontend-e2e-tests**: Set up E2E tests for core flows (upload → OCR → translation)

#### CI/CD Integration

- [ ] **phase2-github-actions-backend**: Create GitHub Actions workflow for Python backend (linting, type checking, tests)
- [ ] **phase2-github-actions-frontend**: Create GitHub Actions workflow for Next.js frontend (linting, type checking, tests)

---

### Phase 3: Architectural Improvements (Weeks 3-4)

#### Reorganize Project Structure

- [ ] **phase3-reorganize-backend-structure**: Move backend Python code into `src/runex/` directory
- [ ] **phase3-consolidate-docs**: Consolidate markdown files into `docs/` directory
- [ ] **phase3-separate-scripts**: Move utility scripts to `scripts/` directory (separate from tests)
- [ ] **phase3-add-init-files**: Add `__init__.py` files to create proper Python packages

#### Pipeline Abstraction

- [ ] **phase3-create-pipeline-class**: Create `OCRPipeline` class for configurable pipeline stages
- [ ] **phase3-add-dependency-injection**: Add dependency injection for OCR and translation engines

**Benefits:** Testable, modular, reusable pipeline

#### Consolidate Translation Modules

- [ ] **phase3-unified-translation-service**: Create unified `TranslationService` using Strategy pattern
- [ ] **phase3-deprecate-old-translators**: Deprecate old translator modules (`translator.py`, `cc_translation.py`)

**Benefits:** Centralizes logic, reduces duplication

#### Remove Global State

- [ ] **phase3-refactor-global-state**: Refactor OCR engine initialization to use constructor injection

**Benefits:** Testable, safe, supports async execution

#### Frontend Architecture

- [ ] **phase3-frontend-api-hooks**: Create/refactor API hooks (`useQuery`, `useMutation`) for clean API integration

---

### Phase 4: Modernization & Performance (Ongoing)

#### Caching & Performance

- [ ] **phase4-add-caching-layer**: Implement cache for image → result mapping (use hash keys or Redis)

**Benefits:** Improves throughput, reduces compute cost

- [ ] **phase4-async-processing**: Use asyncio and ThreadPoolExecutor for parallel OCR/translation

**Benefits:** Non-blocking pipeline, scalable

#### Containerization

- [ ] **phase4-backend-dockerfile**: Create backend Dockerfile for Python/FastAPI service
- [ ] **phase4-docker-compose**: Create full-stack `docker-compose.yml` for backend + frontend

**Benefits:** Reproducible environments, easy deployment

#### Observability

- [ ] **phase4-structured-logging**: Implement structlog or standard structured logging with pipeline stage tracking

**Benefits:** Observability, easier debugging

- [ ] **phase4-opentelemetry**: Add OpenTelemetry for tracing pipeline latencies and errors

**Benefits:** Production-grade monitoring

#### Configuration

- [ ] **phase4-pydantic-settings**: Use `pydantic_settings.BaseSettings` for environment configs
- [ ] **phase4-remove-hardcoded-constants**: Remove hard-coded constants, move to config system

**Benefits:** Flexible deployments, easier testing

---

### Phase 5: Style & Convention (Parallel)

#### Python Style

- [ ] **phase5-pep8-enforcement**: Enforce PEP 8, standardize docstrings to Google style, run black and ruff via CI
- [ ] **phase5-mypy-enforcement**: Enforce type hints with mypy in CI pipeline

#### TypeScript Style

- [ ] **phase5-typescript-strict**: Enforce strict type checking, standardize file naming (kebab-case)
- [ ] **phase5-eslint-prettier**: Add ESLint + Prettier configuration and enforce via CI

#### Documentation

- [ ] **phase5-docs-architecture**: Consolidate markdown files into structured `docs/` with architecture, API, and deployment docs
- [ ] **phase5-developer-guide**: Add developer guide for onboarding and contribution

---

### Phase 6: Future-Proofing

#### LLM Abstraction

- [ ] **phase6-llm-provider-protocol**: Define `LLMProvider` protocol for plug-and-play model upgrades

**Benefits:** Easy model upgrades, extensible architecture

#### Error Handling

- [ ] **phase6-custom-exceptions**: Create custom exception hierarchy (`RuneXError`, `OCRError`, `TranslationError`)

**Benefits:** Centralized error handling, better error messages

#### Performance Monitoring

- [ ] **phase6-performance-monitoring**: Implement performance monitoring with alerts for slow OCR/translation responses

**Benefits:** Proactive issue detection, SLA compliance

---

## Target Directory Structure

After completing all todos, the Rune-X codebase will have the following structure:

```
rune-x/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml      # Python backend CI/CD
│       └── frontend-ci.yml      # Next.js frontend CI/CD
│
├── docs/                        # Consolidated documentation
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── pipeline.md
│   │   └── services.md
│   ├── api/
│   │   ├── endpoints.md
│   │   └── schemas.md
│   ├── deployment/
│   │   ├── docker.md
│   │   └── production.md
│   └── developer-guide.md
│
├── frontend/                     # Next.js application (or keep src/)
│   ├── src/
│   │   ├── app/
│   │   │   ├── api/              # API routes
│   │   │   │   ├── process/
│   │   │   │   │   └── route.ts
│   │   │   │   ├── upload/
│   │   │   │   │   └── route.ts
│   │   │   │   └── ...
│   │   │   ├── auth/
│   │   │   ├── dashboard/
│   │   │   └── upload/
│   │   ├── components/
│   │   │   ├── ui/               # shadcn/ui components
│   │   │   └── providers/
│   │   ├── hooks/                # React hooks
│   │   │   ├── use-api.ts        # API hooks (useQuery, useMutation)
│   │   │   └── use-ocr.ts
│   │   ├── lib/
│   │   │   ├── api-client.ts     # API client utilities
│   │   │   ├── db.ts
│   │   │   └── utils.ts
│   │   └── types/
│   ├── __tests__/                # Frontend tests
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── e2e/
│   ├── jest.config.js
│   ├── jest.setup.js
│   ├── next.config.ts
│   ├── package.json
│   └── tsconfig.json
│
├── src/                          # Python source code
│   └── runex/
│       ├── __init__.py
│       │
│       ├── api/                  # FastAPI routes
│       │   ├── __init__.py
│       │   └── routes.py         # Extracted from main.py
│       │
│       ├── core/                 # Core business logic
│       │   ├── __init__.py
│       │   ├── ocr_service.py    # OCR orchestration
│       │   │   └── Uses: ocr_fusion.py
│       │   ├── translation_service.py  # Translation orchestration
│       │   │   └── Uses: adapters/
│       │   ├── pipeline.py       # Pipeline Orchestration + DI
│       │   ├── ocr_fusion.py     # OCR fusion logic (moved)
│       │   └── adapters/         # Translation adapters
│       │       ├── __init__.py
│       │       ├── marian_adapter.py
│       │       ├── qwen_adapter.py
│       │       └── base.py        # LLMProvider protocol
│       │
│       ├── preprocessing/        # Image preprocessing
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── image_preprocessing.py
│       │
│       ├── models/               # Pydantic models
│       │   ├── __init__.py
│       │   └── schemas.py        # Extracted from main.py
│       │
│       ├── config.py             # Centralized configuration
│       │   └── Uses: pydantic_settings
│       │
│       ├── exceptions.py         # Custom exception hierarchy
│       │
│       └── utils/                # Shared utilities
│           ├── __init__.py
│           └── cache.py          # Caching layer
│
├── tests/                        # All Python tests
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_ocr_fusion.py
│   │   ├── test_translation_service.py
│   │   └── test_preprocessing.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   └── test_pipeline.py
│   ├── e2e/
│   │   └── test_full_pipeline.py
│   ├── performance/
│   │   └── test_ocr_performance.py
│   └── fixtures/
│       └── sample_images.py
│
├── scripts/                      # Utility scripts (non-test)
│   ├── setup/
│   │   └── setup-venv.sh
│   └── maintenance/
│       └── cleanup-old-uploads.py
│
├── infrastructure/               # Infrastructure as code
│   ├── docker/
│   │   ├── Dockerfile.backend
│   │   └── Dockerfile.frontend
│   └── docker-compose.yml
│
├── .env.example                  # Environment variable template
├── .gitignore
├── pyproject.toml                # Python dependency management
├── README.md
└── MODERNIZATION_TODO_AND_STRUCTURE.md  # This file
```

---

## Architecture Overview

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ UI Components│  │  API Hooks   │  │    Pages     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                  │              │
│         └─────────────────┴──────────────────┘             │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             │ HTTP/JSON
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Backend (FastAPI)                     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  API Routes                          │   │
│  │            (api/routes.py)                          │   │
│  └───────┬───────────────┬───────────────┬─────────────┘   │
│          │               │               │                   │
│  ┌───────▼───────┐ ┌────▼──────┐ ┌─────▼──────────┐      │
│  │ OCR Service   │ │Translation │ │   Pipeline     │      │
│  │               │ │  Service   │ │ Orchestration  │      │
│  │ ┌───────────┐ │ │            │ │                │      │
│  │ │OCR Fusion │ │ │ ┌────────┐ │ │ ┌────────────┐│      │
│  │ └───────────┘ │ │ │Adapters│ │ │ │ Dependency ││      │
│  │               │ │ │(Marian,│ │ │ │ Injection  ││      │
│  └───────┬───────┘ │ │ Qwen)   │ │ │ └────────────┘│      │
│          │         │ └────────┘ │ └─────┬──────────┘      │
│          │         │            │       │                   │
│          └─────────┴────────────┴───────┘                   │
│                            │                                │
│                  ┌─────────▼─────────┐                     │
│                  │ Schemas (Pydantic) │                     │
│                  │  (models/schemas.py)│                     │
│                  └────────────────────┘                     │
└────────────────────────────┬────────────────────────────────┘
                              │
                              │ Uses
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Cache Layer   │  │   Async      │  │  Logging &   │     │
│  │(Redis/Hash)  │  │  Processing  │  │  Monitoring  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Docker & CI/CD                               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Configured by
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Configuration (pydantic-settings)                │
│                  (src/runex/config.py)                       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Image Upload
    │
    ▼
[Frontend: Upload Page]
    │
    ▼
[API Route: /api/upload]
    │
    ▼
[Backend: API Routes]
    │
    ▼
[Pipeline Orchestration]
    │
    ├──► [OCR Service]
    │       │
    │       ├──► [Preprocessing]
    │       │
    │       └──► [OCR Fusion]
    │               ├── EasyOCR
    │               └── PaddleOCR
    │
    ├──► [Translation Service]
    │       │
    │       ├──► [Dictionary Lookup]
    │       │
    │       ├──► [MarianMT Adapter]
    │       │
    │       └──► [Qwen Adapter]
    │
    ▼
[Response Assembly]
    │
    ▼
[Frontend: Results Display]
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Establish modular structure and fix critical issues

- Split monolithic `main.py` into focused modules
- Fix TypeScript type safety
- Modernize Python dependency management

**Deliverables:**
- Modular backend structure (`api/`, `core/`, `models/`)
- Type-safe frontend
- `pyproject.toml` with all dependencies

### Phase 2: Quality Assurance (Week 2)
**Goal:** Comprehensive testing infrastructure

- Backend: Unit, integration, performance tests
- Frontend: Component, API route, E2E tests
- CI/CD pipelines for both stacks

**Deliverables:**
- Test suites with coverage reports
- Automated CI/CD workflows
- Test documentation

### Phase 3: Architecture Refinement (Weeks 3-4)
**Goal:** Clean architecture with proper abstractions

- Reorganize project structure
- Create pipeline abstraction
- Consolidate translation modules
- Remove global state

**Deliverables:**
- `src/runex/` package structure
- `OCRPipeline` class with dependency injection
- Unified `TranslationService`
- Frontend API hooks

### Phase 4: Production Readiness (Ongoing)
**Goal:** Performance, observability, and deployment

- Caching layer
- Async processing
- Containerization
- Structured logging and monitoring
- Centralized configuration

**Deliverables:**
- Docker setup
- Performance optimizations
- Monitoring dashboards
- Configuration management

### Phase 5: Code Quality (Parallel)
**Goal:** Consistent style and documentation

- Python: PEP 8, type hints, docstrings
- TypeScript: Strict types, ESLint, Prettier
- Documentation consolidation

**Deliverables:**
- Automated code formatting
- Style guides
- Developer documentation

### Phase 6: Future-Proofing (Ongoing)
**Goal:** Extensibility and maintainability

- LLM provider abstraction
- Custom exception hierarchy
- Performance monitoring

**Deliverables:**
- Extensible LLM interface
- Error handling framework
- Performance metrics

---

## Progress Tracking

### Completion Status

- **Phase 1:** 0/10 tasks (0%)
- **Phase 2:** 0/10 tasks (0%)
- **Phase 3:** 0/10 tasks (0%)
- **Phase 4:** 0/8 tasks (0%)
- **Phase 5:** 0/6 tasks (0%)
- **Phase 6:** 0/3 tasks (0%)

**Overall:** 0/47 tasks (0%)

### Next Steps

1. **Start with Phase 1, Task 1:** Split `main.py` - Extract API routes
2. **Set up tracking:** Use GitHub Projects or similar to track progress
3. **Regular reviews:** Review progress weekly and adjust priorities as needed

---

## Notes

- **Estimated Timeline:** 6-8 weeks for Phases 1-3, ongoing for Phases 4-6
- **Dependencies:** Some tasks can be done in parallel (e.g., Phase 5 style tasks)
- **Priority:** Phase 1 is critical and should be completed first
- **Testing:** Each phase should include testing to ensure no regressions

---

**Last Updated:** December 2025  
**Maintained By:** Rune-X Development Team
