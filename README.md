# SENTINEL2

Autonomous strategic intelligence pipeline for the Greater Middle East and Caucasus region.

## Quick Start

```bash
# 1. Clone and enter
git clone https://github.com/PrestonDihle/Sentinal2.git
cd Sentinal2

# 2. Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 5. Start MySQL
docker compose up -d

# 6. Seed database
python -m src.db.seed

# 7. Run pipeline
python -m src.pipeline
```

## Architecture

- **Layer 1:** Collection Management (CMA Agent with active tools)
- **Layer 2:** GDELT Ingest + Metrics + Processing
- **Layer 3:** 6 Analysis Groups (49 expert agents, Tree of Thought)
- **Layer 4:** Reporting + Delivery (PDF → Drive → Gmail)

## Model Routing

| Component | Model | Provider |
|-----------|-------|----------|
| Collection/Processing | Gemini 2.5 Flash | Google |
| Analysis Groups 1-5 | Claude Sonnet | Anthropic |
| Big Question (Group 6) | Claude Opus | Anthropic |
| CMA / Planner | Claude Sonnet | Anthropic |
| Reporter | Gemini 2.5 Flash | Google |
