# Warden - Complete Design Document

**AI Agent for Continuous Codebase Vigilance**

**Version:** 1.0
**Date:** January 2024
**Status:** Design Phase
**License:** MIT

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Vision & Positioning](#vision--positioning)
3. [Design Objectives](#design-objectives)
4. [System Architecture](#system-architecture)
5. [Technical Specifications](#technical-specifications)
6. [Configuration Reference](#configuration-reference)
7. [Implementation Roadmap](#implementation-roadmap)
8. [API Reference](#api-reference)
9. [Appendices](#appendices)

---

## Executive Summary

### What is Warden?

**Warden** is a continuous AI agent system that maintains persistent watch over a codebase, proactively improving code
quality and surfacing insights without explicit user requests.

**Key Insight:** Unlike request-response AI tools (Copilot, ChatGPT), Warden runs as a background daemon that builds deep
understanding over time and acts autonomously.

### Core Capabilities

🛡️ **Continuous Understanding**
- Extracts design philosophy from every commit
- Tracks architectural evolution automatically
- Detects and catalogs code patterns
- Maintains living documentation

🔧 **Autonomous Improvement**
- Identifies performance bottlenecks (O(n²) → O(n log n))
- Flags security vulnerabilities before production
- Improves documentation coverage
- Creates draft PRs for human review (never auto-merges)

📡 **Proactive Monitoring**
- Alerts on critical security vulnerabilities within 24 hours
- Recommends relevant trending libraries/patterns
- Detects breaking changes in dependencies
- Prepares non-breaking dependency upgrade PRs

🧠 **Persistent Memory**
- Never forgets context between sessions
- Learns from user feedback and rejections
- Builds semantic understanding of codebase over weeks

### Differentiator

**Warden shifts from "AI waits for you" to "AI keeps vigil alongside you."**

Like a faithful guardian, Warden maintains continuous watch, understanding your codebase's history, protecting its
quality, and suggesting improvements autonomously.

---

## Vision & Positioning

### The Problem

Developers have powerful AI coding assistants (Copilot, Cursor, ChatGPT), but these tools:
- **Wait for requests** - Only activate when explicitly invoked
- **Lose context** - Forget previous conversations when session ends
- **Don't understand history** - Can't reference why code was designed a certain way
- **Require prompting** - Developer must know what to ask for

**Result:** AI acts as a reactive helper, not a proactive guardian.

### The Warden Solution

Warden inverts this model:
- **Always running** - Background daemon that never sleeps
- **Persistent memory** - Builds understanding over days/weeks/months
- **Historical awareness** - References commit history and design decisions
- **Autonomous action** - Suggests improvements without being asked

**Mental Model:** Warden is like a senior engineer who:
- Reviews every commit as it comes in
- Remembers past architectural discussions
- Proactively flags issues before they become problems
- Suggests improvements based on team patterns

### Why "Warden"?

A **warden** is a guardian who maintains continuous watch over what they protect. Unlike a guard who patrols periodically,
a warden has:
- **Enduring responsibility** - Never abandons their post
- **Deep knowledge** - Understands the domain intimately
- **Authority** - Trusted to make decisions autonomously
- **Protective duty** - Guards against threats and degradation

These qualities perfectly capture Warden's role in a codebase.

### Inspiration: The "Workflow Layer" Pattern

Warden follows the pattern established by tools like oh-my-zsh and oh-my-codex:

**Don't replace what works. Add opinionated workflow on top.**

- Warden doesn't replace git, your editor, or CI/CD
- It adds a **continuous intelligence layer** that sits on top
- Existing workflows continue unchanged
- Warden enhances them with autonomous understanding and improvement

---

## Design Objectives

### 1. Continuous Awareness

**Objective:** Build and maintain deep understanding of codebase without explicit user requests.

**Success Criteria:**
- [ ] Warden can answer "Why was X designed this way?" by citing specific commits
- [ ] Architecture map stays current with codebase changes (< 1 hour lag)
- [ ] Pattern detection identifies recurring patterns within 3 commits
- [ ] Design philosophy document reflects team decisions from PR comments
- [ ] Understanding persists and accumulates over weeks/months

**Non-Goals:**
- Perfect understanding on day 1 (builds incrementally)
- Understanding without any signal (requires commit messages/comments)
- Mind-reading developer intent (makes educated guesses, not certainties)

**How Measured:**
- User queries: "Why did we choose async/await?" → Warden cites commit abc123
- Architecture visualization accuracy validated by team lead
- Pattern detection recall/precision on manual review

---

### 2. Autonomous Improvement

**Objective:** Identify and fix quality issues without explicit user commands.

**Success Criteria:**
- [ ] Creates draft PRs for performance issues with 90%+ accuracy
- [ ] Flags security vulnerabilities with <5% false positive rate
- [ ] Improves documentation coverage measurably (docstring % increase)
- [ ] Never auto-merges (100% human approval required)
- [ ] Users accept 70%+ of improvement suggestions

**Non-Goals:**
- Fixing every minor style issue (focus on high-impact improvements)
- Replacing human code review (augments review, provides first pass)
- Perfect fixes every time (95% correct acceptable, human validates)

**How Measured:**
- PR acceptance rate (target: 70%+)
- False positive rate on security findings (target: <5%)
- Time saved in code review (survey developers)

---

### 3. Proactive Intelligence

**Objective:** Surface external insights before user needs to look for them.

**Success Criteria:**
- [ ] Notifies critical CVEs within 24 hours of publication
- [ ] Recommends trending tools with >80% relevance score (user feedback)
- [ ] Detects breaking changes in dependencies before attempted upgrade
- [ ] Prepares upgrade PRs that pass CI on first attempt (70%+ rate)

**Non-Goals:**
- Notifying on every dependency patch version (filter for relevance)
- Predicting future trends (focus on actionable present insights)
- Making upgrade decisions (user decides, Warden prepares)

**How Measured:**
- CVE notification latency (target: <24 hours)
- Trend recommendation relevance score (user ratings)
- Upgrade PR success rate (target: 70%+ pass CI)

---

### 4. Resource Efficiency

**Objective:** Run continuously without degrading developer experience.

**Success Criteria:**
- [ ] CPU usage <10% when user actively coding
- [ ] Memory footprint <2GB
- [ ] LLM token budget <$5/day for typical project (10 commits/day)
- [ ] Pauses heavy processing when user activity detected
- [ ] No noticeable impact on git performance

**Non-Goals:**
- Zero resource usage (some overhead necessary)
- Instant responses (background processing can be delayed)
- Free operation (LLM costs unavoidable, but minimize)

**How Measured:**
- CPU/memory monitoring (target: <10% CPU, <2GB RAM)
- Daily cost tracking (target: <$5/day)
- User surveys on perceived impact

---

### 5. User Control & Trust

**Objective:** Users trust Warden because they maintain full control.

**Success Criteria:**
- [ ] All autonomous changes go through draft PRs (0 auto-merges)
- [ ] User can pause/resume Warden instantly
- [ ] Clear visibility into what Warden is doing (dashboard/logs)
- [ ] Users can mark suggestions as good/bad, Warden learns
- [ ] Warden respects .wardenignore for sensitive files

**Non-Goals:**
- Fully autonomous operation without oversight
- Replacing human judgment on design decisions
- Access to secrets/credentials (explicitly blocked)

**How Measured:**
- Auto-merge count (must be 0)
- User feedback loop adoption rate
- Trust surveys (target: 80%+ trust Warden's suggestions)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Developer                             │
│                  (writes code, reviews PRs)                  │
└────────────┬───────────────────────────────────┬────────────┘
             │                                   │
             │ git commit                        │ review/approve
             │                                   │
        ┌────▼────────────────────────────────┐ │
        │     Git Repository + Hooks          │ │
        └────┬────────────────────────────────┘ │
             │                                   │
             │ triggers events                   │
             │                                   │
┌────────────▼───────────────────────────────────▼────────────┐
│                    Warden Core Engine                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Event       │  │ State       │  │ Task        │         │
│  │ Listener    │──│ Manager     │──│ Scheduler   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Agent Process Pool                       │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │  │
│  │  │Understand│  │ Improve │  │ Monitor │  │ Learn   │ │  │
│  │  │ Agent   │  │ Agent   │  │ Agent   │  │ Agent   │ │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              LLM Interface Layer                      │  │
│  │  • Model routing (GPT-4 / Claude / local)            │  │
│  │  • Token budget management                            │  │
│  │  • Response caching                                   │  │
│  │  • Cost tracking                                      │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────┬─────────────────────────────────┬─────────────┘
             │                                  │
             │ reads/writes                     │ creates
             │                                  │
        ┌────▼────────────┐              ┌─────▼──────────┐
        │ .warden/        │              │ Draft PRs      │
        │ • understanding/│              │ (GitHub)       │
        │ • state.db      │              │                │
        │ • vector.db/    │              │                │
        │ • logs/         │              │                │
        └─────────────────┘              └────────────────┘
```

### Component Breakdown

#### 1. **Warden Core Engine**
- **Role:** Central orchestrator, lifecycle manager
- **Responsibilities:**
  - Start/stop/restart daemon
  - Route events to appropriate handlers
  - Coordinate state management
  - Enforce resource limits
  - Graceful shutdown

#### 2. **Event Listener**
- **Role:** Detect trigger conditions
- **Trigger Sources:**
  - Git hooks (post-commit, post-merge, post-checkout)
  - File system watcher (file changes)
  - Cron scheduler (time-based tasks)
  - Manual CLI invocations

#### 3. **State Manager**
- **Role:** Persistent storage and retrieval
- **Storage Layers:**
  - **SQLite:** Structured data (timelines, config, metadata)
  - **ChromaDB:** Semantic search (code patterns, similar issues)
  - **File system:** Generated artifacts (`.warden/understanding/*.md`)
- **State Includes:**
  - Understanding (architecture, design philosophy, patterns)
  - Improvement history (opportunities, completed, declined)
  - Monitoring data (dependencies, vulnerabilities, trends)
  - User preferences (learned from feedback)

#### 4. **Agent Pool**
- **Role:** Execute specialized tasks
- **Agents:**
  - **UnderstandAgent:** Extract design decisions, build architecture map
  - **ImproveAgent:** Detect issues, generate fixes, create draft PRs
  - **MonitorAgent:** Watch external sources (CVEs, trends, deps)
  - **LearnAgent:** Analyze user feedback, update preferences
- **Resource Management:**
  - Token budgets (max per day/task)
  - CPU throttling (pause when user coding)
  - Concurrency limits (max N agents simultaneously)

#### 5. **LLM Interface Layer**
- **Role:** Abstract model providers, optimize costs
- **Features:**
  - Model routing (GPT-4 for complex, GPT-3.5 for simple, local for cheap)
  - Response caching (semantic + exact match)
  - Token budget tracking
  - Cost attribution (per agent/task)

---

## Technical Specifications

### Technology Stack

**Core Framework:**
- **Language:** Python 3.11+
- **Async:** asyncio (all I/O operations async)
- **CLI:** Typer (modern CLI interface)
- **Config:** Pydantic (type-safe configuration)

**Storage:**
- **Relational:** SQLAlchemy + SQLite (structured state)
- **Vector:** ChromaDB (semantic code search)
- **Cache:** In-memory LRU cache (hot data)

**LLM Integration:**
- **Primary:** OpenAI (GPT-4, GPT-3.5-turbo)
- **Secondary:** Anthropic Claude (alternative)
- **Local:** llama-cpp-python (CodeLlama for cheap tasks)

**Git & GitHub:**
- **Git:** GitPython (repository operations)
- **GitHub:** PyGithub (PR creation, API access)

**Monitoring & Notifications:**
- **HTTP:** aiohttp (async API calls)
- **Scheduling:** APScheduler (cron jobs)
- **Slack:** slack-sdk (notifications)
- **RSS:** feedparser (blog monitoring)

**Embeddings:**
- **Models:** sentence-transformers (local embeddings)
- **Purpose:** Semantic similarity for code patterns

### Project Structure

```
warden/
├── warden/                      # Main package
│   ├── __init__.py
│   ├── core/                    # Core engine components
│   │   ├── engine.py            # WardenEngine orchestrator
│   │   ├── event_listener.py   # Event detection & routing
│   │   ├── state_manager.py    # Persistent state management
│   │   ├── task_scheduler.py   # Cron scheduling
│   │   └── agent_pool.py       # Agent lifecycle & execution
│   │
│   ├── agents/                  # Specialized agents
│   │   ├── base.py              # Abstract Agent base class
│   │   ├── understand.py        # UnderstandAgent
│   │   ├── improve.py           # ImproveAgent
│   │   ├── monitor.py           # MonitorAgent
│   │   └── learn.py             # LearnAgent
│   │
│   ├── llm/                     # LLM abstraction layer
│   │   ├── interface.py         # Unified LLM interface
│   │   ├── router.py            # Model selection logic
│   │   ├── cache.py             # Response caching
│   │   └── budget.py            # Token budget tracking
│   │
│   ├── git/                     # Git integration
│   │   ├── hooks.py             # Git hook handlers
│   │   ├── repository.py        # Repo operations wrapper
│   │   └── github_client.py    # GitHub API client
│   │
│   ├── monitoring/              # External monitoring
│   │   ├── dependencies.py      # npm/pip dependency checks
│   │   ├── security.py          # CVE vulnerability scanning
│   │   ├── trends.py            # GitHub trending, RSS
│   │   └── notifier.py          # Slack/email notifications
│   │
│   ├── models/                  # Data models
│   │   ├── state.py             # WardenState (Pydantic)
│   │   ├── config.py            # WardenConfig (Pydantic)
│   │   └── tasks.py             # Task definitions
│   │
│   ├── cli/                     # Command-line interface
│   │   └── commands.py          # Typer CLI commands
│   │
│   └── utils/                   # Utilities
│       └── logging.py           # Logging configuration
│
├── .warden/                     # Runtime directory (in user's repo)
│   ├── config.yml               # User configuration
│   ├── state.db                 # SQLite database
│   ├── vector.db/               # ChromaDB storage
│   ├── understanding/           # Generated documentation
│   │   ├── architecture.md
│   │   ├── design-philosophy.md
│   │   └── patterns.md
│   ├── queue/                   # Task queue persistence
│   └── logs/                    # Execution logs
│
├── tests/                       # Test suite
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/                        # Documentation
├── examples/                    # Example repositories
├── pyproject.toml               # Package configuration
├── README.md
└── LICENSE
```

### Data Flow: Commit Event Example

**Scenario:** Developer commits change to `api/orders.py`

```
1. Developer: git commit -m "Optimize order query"
   │
2. Git Hook: post-commit fires
   │
3. EventListener.on_commit(commit_hash="abc123")
   │
4. TaskScheduler.enqueue()
   │
   ├─> Task: {type: "understand", priority: "medium", delay: 0s}
   │   └─> AgentPool assigns Worker-0
   │       └─> UnderstandAgent.execute()
   │           ├─> Read commit message + diff
   │           ├─> LLM: Extract design decision
   │           │   Prompt: "Why was this optimization made?"
   │           │   Response: "Reduced O(n²) to O(n log n) for large datasets"
   │           ├─> StateManager.update_understanding()
   │           │   └─> Save to .warden/understanding/design-philosophy.md
   │           └─> Return: {success: true, tokens: 1,234}
   │
   └─> Task: {type: "improve", priority: "low", delay: 5s}
       └─> AgentPool assigns Worker-1 (after 5s delay)
           └─> ImproveAgent.execute()
               ├─> Analyze api/orders.py for issues
               ├─> LLM: Check for problems
               │   Found: Missing index on user_id column (database)
               ├─> LLM: Generate migration
               ├─> Create branch: warden/improve-db-index-1234
               ├─> Write migration file
               ├─> git commit + push
               ├─> GitHub: Create draft PR #847
               └─> Notify user: "🛡️ Warden created draft PR: Add index to orders.user_id"

5. Developer reviews PR #847
   │
6. Developer approves & merges
   │
7. LearnAgent observes:
   └─> User accepted database optimization
   └─> Increase confidence in similar patterns
   └─> Update preferences: user values performance > query simplicity
```

---

## Configuration Reference

### Configuration File

Location: `.warden/config.yml`

### Complete Schema

```yaml
# Operation Modes
modes:
  understanding:
    enabled: true
    trigger: on_commit  # on_commit | hourly | daily
    processes:
      - codebase-map      # Track component relationships
      - design-extraction # Extract from commits/PRs
      - pattern-learning  # Detect recurring patterns

  improvement:
    enabled: true
    trigger: after_commit  # after_commit | daily
    max_draft_prs: 5       # Max concurrent draft PRs
    require_approval: true # Never auto-merge
    checks:
      - performance        # O(n²) optimizations
      - security          # SQL injection, XSS
      - documentation     # Missing docstrings
      - test-coverage     # Untested paths

  trends:
    enabled: true
    cadence: weekly        # daily | weekly
    sources:
      - github_trending    # Trending repos
      - dependency_updates # npm/pip updates
      - security_advisories # CVE alerts
    notification_threshold: medium # low | medium | high

# Resource Management
resources:
  token_budget:
    daily: 100000          # Max tokens per day (~$5)
    per_task: 10000        # Max tokens per task

  max_cpu_percent: 80      # Pause if CPU > 80%
  max_memory_mb: 2048      # Max 2GB RAM

  concurrency:
    max_agents: 3          # Max concurrent workers

  pause_when_coding: true  # Detect user activity
  resume_after_idle_sec: 300 # Resume after 5min idle

# Notifications
notifications:
  channels:
    critical: slack        # Security vulnerabilities
    important: slack       # Draft PRs, breaking changes
    informational: weekly_digest # Trends, suggestions

  slack_webhook: https://hooks.slack.com/services/YOUR/WEBHOOK
  email: your@email.com

# LLM Configuration
llm:
  openai_api_key: sk-...
  anthropic_api_key: null  # Optional Claude access
  default_model: gpt-4     # gpt-4 | gpt-3.5-turbo | claude
  use_local_models: false  # Use CodeLlama for cheap tasks

# Git Integration
git:
  auto_install_hooks: true
  ignore_patterns:
    - "*.lock"
    - "node_modules/**"
    - ".env*"
    - "secrets/**"

# GitHub Integration
github:
  enabled: false
  token: ghp_...           # GitHub personal access token
  create_draft_prs: true   # Create draft PRs automatically
  auto_merge_non_breaking: false # Never auto-merge (safety)
```

### Configuration Presets

**Minimal (Development):**
```yaml
modes:
  understanding:
    enabled: true

resources:
  token_budget:
    daily: 50000  # ~$2.50/day

llm:
  openai_api_key: sk-...
  default_model: gpt-3.5-turbo  # Cheaper
```

**Recommended (Production):**
```yaml
modes:
  understanding:
    enabled: true
    trigger: on_commit
  improvement:
    enabled: true
    max_draft_prs: 3
  trends:
    enabled: true
    cadence: weekly

resources:
  token_budget:
    daily: 100000
  pause_when_coding: true

notifications:
  channels:
    critical: slack
  slack_webhook: https://...

llm:
  openai_api_key: sk-...
  default_model: gpt-4
```

---

## Implementation Roadmap

### MVP (Week 1) - Prove the Concept

**Goal:** Demonstrate that continuous understanding extraction works.

**Scope:**
- ✅ Core engine (start/stop daemon)
- ✅ EventListener (git commit detection)
- ✅ StateManager (SQLite persistence)
- ✅ UnderstandAgent (design extraction)
- ✅ CLI (init, start, stop, status)
- ✅ Basic LLM integration (OpenAI)

**Not in MVP:**
- ❌ ImproveAgent (defer to v0.2)
- ❌ MonitorAgent (defer to v0.2)
- ❌ Vector DB (defer to v0.2)
- ❌ Multiple workers (defer to v0.2)
- ❌ Notifications (defer to v0.2)

**Success Metrics:**
- [ ] User can `warden init` and `warden start`
- [ ] After 5 commits, `.warden/understanding/design-philosophy.md` has meaningful content
- [ ] Token usage < $0.50/day for typical development (10 commits)
- [ ] Daemon runs 8+ hours without crashing

**Timeline:**
- Day 1: Core engine + project setup
- Day 2: StateManager + EventListener
- Day 3: LLM integration + UnderstandAgent
- Day 4: CLI + AgentPool (single worker)
- Day 5: Polish, testing, documentation

---

### v0.2 (Week 2-3) - Add Autonomous Improvements

**Goal:** Demonstrate that Warden can create useful draft PRs.

**Scope:**
- ✅ ImproveAgent (performance, security, docs)
- ✅ GitHub integration (draft PR creation)
- ✅ Multiple workers (3 concurrent agents)
- ✅ Resource throttling (CPU/memory limits)
- ✅ Notifications (Slack integration)

**Success Metrics:**
- [ ] 70%+ of improvement PRs accepted by users
- [ ] <5% false positive rate on security findings
- [ ] Draft PRs pass CI on first attempt (70%+ rate)

---

### v0.3 (Week 4-5) - Add Proactive Monitoring

**Goal:** Warden watches external world and surfaces insights.

**Scope:**
- ✅ MonitorAgent (dependencies, CVEs, trends)
- ✅ Weekly digest emails
- ✅ Auto-upgrade PRs for non-breaking changes
- ✅ Vector DB (semantic code search)

**Success Metrics:**
- [ ] CVE alerts within 24 hours of publication
- [ ] Trend recommendations rated >80% relevant
- [ ] Users enable weekly digest (adoption metric)

---

### v0.4 (Week 6-7) - Learning & Refinement

**Goal:** Warden adapts to team preferences.

**Scope:**
- ✅ LearnAgent (analyze feedback, update preferences)
- ✅ User feedback UI (thumbs up/down on suggestions)
- ✅ Confidence scoring (only surface high-confidence items)
- ✅ Team-specific pattern learning

**Success Metrics:**
- [ ] Suggestion acceptance rate improves 10%+ after learning
- [ ] Users actively provide feedback (>50% engagement)

---

### v1.0 (Week 8+) - Production Ready

**Goal:** Stable, scalable, enterprise-ready.

**Scope:**
- ✅ Multi-repo support (monorepos)
- ✅ Role-based access control (RBAC)
- ✅ Audit logging
- ✅ Distributed deployment (multiple machines)
- ✅ Cost optimization (aggressive caching, local models)
- ✅ SLA commitments (uptime, latency)

**Success Metrics:**
- [ ] 99.9% uptime
- [ ] <$10/day for large team (50 devs, 100 commits/day)
- [ ] Adoption by 5+ production teams

---

## API Reference

### Core Engine

```python
from warden.core.engine import WardenEngine
from pathlib import Path

# Initialize
engine = WardenEngine(
    repo_path=Path("/path/to/repo"),
    config_path=Path(".warden/config.yml")  # Optional
)

# Lifecycle
await engine.start()  # Start all components
await engine.stop()   # Graceful shutdown
```

### State Manager

```python
from warden.core.state_manager import StateManager

state = StateManager(db_path=Path(".warden/state.db"))

# Load/persist
await state.load()
await state.persist()

# Update understanding
await state.update_understanding({
    "design_philosophy": [{
        "principle": "Use async/await",
        "rationale": "...",
        "commit": "abc123"
    }]
})

# Semantic search
patterns = await state.find_similar_patterns(code, top_k=5)
```

### Agents

```python
from warden.agents.understand import UnderstandAgent

agent = UnderstandAgent(state_manager, config)

result = await agent.execute(
    task={"type": "understand", "data": {"commit_hash": "abc123"}},
    budget=ResourceBudget(max_tokens=10000)
)

# result = {
#     "success": True,
#     "summary": "Extracted 1 design decision",
#     "tokens_used": 1234
# }
```

### CLI Commands

```bash
# Initialize Warden in current repo
warden init

# Start daemon (foreground)
warden start

# Start daemon (background)
warden start --daemon

# Check status
warden status

# Stop daemon
warden stop

# Reload configuration
warden reload

# Show configuration
warden config

# Validate configuration
warden config validate
```

---

## Appendices

### A. Comparison with Existing Tools

| Feature | GitHub Copilot | Cursor | ChatGPT | Warden |
|---------|---------------|--------|---------|--------|
| **Mode** | Reactive | Reactive | Reactive | Proactive |
| **Runs when** | You type | You ask | You prompt | Always |
| **Memory** | None | Session | Conversation | Permanent |
| **Understands history** | No | No | No | Yes (git) |
| **Autonomous action** | No | No | No | Yes (draft PRs) |
| **Cost model** | $10-20/mo | $20/mo | $20/mo | Usage-based (~$5/day) |

**Warden's niche:** The only tool that maintains continuous watch and acts autonomously.

---

### B. Security & Privacy

**Sensitive Data Handling:**
- Warden respects `.wardenignore` (like `.gitignore`)
- Never sends API keys/secrets to LLM
- Detects common secret patterns and excludes from prompts
- Local processing for sensitive operations (optional)

**Data Storage:**
- All state stored locally in `.warden/`
- No data sent to Warden servers (doesn't exist)
- LLM providers (OpenAI) see code snippets per terms of service
- Encryption at rest for sensitive fields (API keys)

**Access Control:**
- Warden runs with same permissions as user
- No elevated privileges required
- GitHub token stored securely (OS keychain integration)

---

### C. Cost Analysis

**Token Usage Estimates:**

| Activity | Tokens | Cost (GPT-4) |
|----------|--------|--------------|
| Extract design decision | 500-1,000 | $0.03-0.06 |
| Analyze file for issues | 1,000-3,000 | $0.06-0.18 |
| Generate fix | 500-2,000 | $0.03-0.12 |
| Monitor trends | 200-500 | $0.01-0.03 |

**Daily Budget (Typical Team):**
- 10 commits/day
- 3 improvements generated
- 1 monitoring cycle

**Total:** ~50,000 tokens/day = **$2-3/day**

**Optimization Strategies:**
- Use GPT-3.5 for simple tasks (10x cheaper)
- Aggressive caching (semantic similarity)
- Local models for syntax/pattern matching
- Batch operations during low-activity periods

**Target:** <$5/day for typical project, <$10/day for large teams

---

### D. Failure Modes & Mitigations

**Failure Mode 1: LLM Hallucinates Design Decision**
- **Impact:** Incorrect understanding documented
- **Mitigation:** Cite source commits, allow user corrections
- **Recovery:** User edits `.warden/understanding/*.md`, Warden learns

**Failure Mode 2: Improvement PR Breaks CI**
- **Impact:** Wasted review time
- **Mitigation:** Draft PR only, human reviews before merge
- **Recovery:** User declines PR, Warden lowers confidence

**Failure Mode 3: Token Budget Exhausted**
- **Impact:** Warden stops processing
- **Mitigation:** Priority queue (critical tasks first)
- **Recovery:** Resume next day, backlog processed

**Failure Mode 4: Daemon Crash**
- **Impact:** Loss of in-flight tasks
- **Mitigation:** Write-ahead log, state persistence
- **Recovery:** On restart, resume from checkpoint

**Failure Mode 5: False Positive Security Alert**
- **Impact:** Unnecessary alarm
- **Mitigation:** Confidence scoring, review before alerting
- **Recovery:** User marks false positive, Warden learns

---

### E. Future Directions

**Post-v1.0 Possibilities:**

1. **Multi-Language Support**
   - Currently Python-focused
   - Expand to JavaScript, Go, Rust, Java

2. **Team Collaboration**
   - Shared understanding across team members
   - Warden syncs knowledge via central server

3. **Custom Agents**
   - User-defined agents via plugin system
   - Domain-specific checks (e.g., healthcare compliance)

4. **IDE Integration**
   - VSCode extension showing Warden insights inline
   - Real-time feedback as you code

5. **Predictive Suggestions**
   - "Based on this change, you'll likely need to update X"
   - Proactive refactoring recommendations

6. **Code Review Assistance**
   - Warden reviews PRs before human reviewers
   - Flags issues, suggests improvements

---

## Conclusion

**Warden represents a paradigm shift in AI-assisted development:**

From **reactive assistance** (Copilot, ChatGPT) to **proactive guardianship**.

**Key Innovation:** Continuous operation + persistent memory + autonomous action

**Value Proposition:**
- Developers keep coding as usual
- Warden maintains vigilance in the background
- Code quality improves without extra effort
- Institutional knowledge captured automatically

**Next Step:** Build MVP to validate core hypothesis - can continuous understanding extraction provide meaningful value?

---

**Document Version:** 1.0
**Last Updated:** January 2024
**Status:** Ready for Implementation
**Contact:** [Project maintainer contact]

---

*End of Design Document*