# Calorie Tracker

A wellness-focused calorie tracker with multi-agent AI architecture for meal analysis and energy balance tracking.

## Overview

This application combines computer vision, large language models, and multi-agent orchestration to provide personalized nutrition insights. The system emphasizes safety and privacy by using ranges instead of exact measurements and enforcing strict guardrails against eating disorder triggers.

## Architecture

### Tech Stack

- **Backend**: FastAPI (Python 3.10+) with async/await
- **Frontend**: React 19 + Vite
- **Database**: SQLite with SQLAlchemy ORM (async)
- **Vision Model**: Google Gemini 2.0 Flash
- **Text Generation**: Groq Llama 3.1 70B
- **Observability**: Opik (full trace logging)
- **Authentication**: JWT with bcrypt password hashing

### Multi-Agent System

The application uses 10 specialized agents coordinated through a central orchestrator:

**Core Pipeline (Meal Analysis)**:
1. Vision Interpreter - Identifies food items and estimates portions from images
2. Nutrition Reasoner - Calculates calorie ranges and macro distribution using USDA FDC data
3. Personalization Agent - Contextualizes nutrition data with user profile and daily meals
4. Wellness Coach - Generates supportive feedback with enforced safety rules

**Advanced Agents**:
- Drift Detector - Identifies behavioral patterns and deviations
- Next Action Agent - Recommends contextual next steps
- Strategy Adapter - Adapts recommendations based on engagement
- Energy Intervention - Provides energy-focused guidance
- Weekly Reflection - Generates weekly insights and goal recommendations
- Goal Guardian - Ensures recommendations align with user goals

All agent decisions are traced in Opik for complete observability and model improvement tracking.

## Design Principles

**Safety First**: Strict guardrails prevent eating disorder triggers. No calorie minimums/maximums, no body shaming, no medical advice.

**Privacy Preserving**: User profiles store ranges (age_range, height_range, weight_range) instead of exact measurements.

**Observability**: Every AI decision is traced in Opik for transparency and model improvement.

**Async Throughout**: Non-blocking operations for image processing, LLM calls, and database queries.

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Google Gemini API key (free at https://aistudio.google.com/)
- Opik account (free at https://www.comet.com/signup)
- USDA FDC API key (free at https://fdc.nal.usda.gov/api-key-signup)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
# GOOGLE_API_KEY=your_key
# GROQ_API_KEY=your_key
# OPIK_API_KEY=your_key
# OPIK_WORKSPACE=your_workspace
# FDC_API_KEY=your_key
# JWT_SECRET_KEY=your_secret

# Run backend
uvicorn main:app --reload
```

Backend runs at http://localhost:8000 with API docs at http://localhost:8000/docs

### Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

Frontend runs at http://localhost:5173

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login (returns JWT token)
- `GET /auth/me` - Get current user

### Profile
- `GET /profile` - Get user profile
- `PUT /profile` - Update profile (age_range, height_range, weight_range, activity_level, goal)
- `GET /profile/options` - Get valid options for form building

### Meal Analysis
- `POST /analyze/meal` - Analyze meal photo (orchestrates all agents)
- `POST /analyze/barcode` - Quick barcode scan for packaged foods
- `GET /analyze/history` - Get meal history (paginated)
- `GET /analyze/meal/{id}` - Get detailed analysis for specific meal

### Feedback
- `POST /feedback` - Submit feedback for meal analysis
- `GET /feedback/meal/{id}` - Get feedback for specific meal
- `GET /feedback/stats` - Get feedback statistics

### Balance
- `GET /balance/today` - Today's energy balance summary
- `GET /balance/week` - Weekly balance breakdown
- `GET /balance/reflection/weekly` - AI-powered weekly reflection

## Database Schema

**Users**: Email, hashed password, profile ranges (age, height, weight, activity level, goal)

**Meals**: Image data, context, agent analysis results (stored as JSON), confidence scores

**Feedbacks**: Meal reference, feedback type (accurate/portion_bigger/portion_smaller/wrong_food), comment

**DailyBalances**: User reference, date, calorie ranges, balance status, reasoning

## Food Database

The application uses a dual-source food database with intelligent fallback:

**Primary Source**: USDA FDC (raw ingredients, verified data)
- Comprehensive nutrition data for unprocessed foods
- Reliable baseline for macro calculations
- Free API with key registration

**Fallback Source**: Open Food Facts (packaged foods, barcodes)
- 2.5M+ packaged food products
- Barcode lookup (EAN/UPC)
- Community-maintained, constantly updated
- No API key required

**Lookup Chain**:
1. Try USDA FDC by food name (raw ingredients)
2. If not found, try Open Food Facts by name (packaged foods)
3. If barcode provided, direct Open Food Facts barcode lookup
4. Results cached for 7 days to reduce API calls

This approach ensures coverage for both raw ingredients and packaged foods while maintaining data quality.

## Meal Analysis Flow

**Photo Analysis**:
1. User uploads image via frontend
2. Frontend converts to base64, sends to `/analyze/meal`
3. Backend orchestrator chains agents:
   - Vision Interpreter identifies foods and portions
   - Nutrition Reasoner calculates calorie ranges (queries USDA FDC, falls back to Open Food Facts)
   - Personalization Agent contextualizes with user profile and daily meals
   - Wellness Coach generates supportive feedback with safety checks
   - Advanced agents provide drift detection, next actions, strategy adaptation
4. All results logged to Opik with full trace
5. Results stored in database
6. Response sent to frontend with foods, calorie ranges, balance status, message, suggestions
7. User provides feedback (accurate/portion_bigger/etc.)
8. Feedback logged to Opik for model improvement

**Barcode Scanning**:
1. User scans barcode via frontend
2. Frontend sends barcode to `/analyze/barcode`
3. Backend queries Open Food Facts directly
4. Creates synthetic vision result with verified nutrition data
5. Runs through personalization and wellness agents
6. Returns personalized analysis (balance status, supportive message)
7. Stores in database with full meal record
8. User gets same personalized experience as photo analysis

## Configuration

Environment variables in `.env`:

- `GOOGLE_API_KEY` - Google Gemini API key
- `GROQ_API_KEY` - Groq API key for text generation
- `OPIK_API_KEY` - Opik observability API key
- `OPIK_WORKSPACE` - Opik workspace name
- `OPIK_URL_OVERRIDE` - Opik API URL (default: https://www.comet.com/opik/api)
- `FDC_API_KEY` - USDA Food Data Central API key
- `JWT_SECRET_KEY` - Secret key for JWT signing
- `JWT_ALGORITHM` - JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration (default: 1440 = 24 hours)
- `DATABASE_URL` - SQLite connection string (default: sqlite+aiosqlite:///./calorie_tracker.db)

## Project Structure

```
backend/
├── main.py                    # FastAPI application
├── config.py                  # Settings management
├── database.py                # SQLAlchemy setup
├── models.py                  # Database models
├── schemas.py                 # Pydantic schemas
├── auth.py                    # JWT authentication
├── constants.py               # Application constants
├── agents/                    # Multi-agent system
│   ├── base.py               # Base agent class
│   ├── orchestrator.py        # Main orchestrator
│   ├── vision_interpreter.py  # Food identification
│   ├── nutrition_reasoner.py  # Calorie calculation
│   ├── personalization_agent.py
│   ├── wellness_coach.py      # Supportive feedback
│   ├── drift_detector.py
│   ├── next_action_agent.py
│   ├── strategy_adapter.py
│   ├── energy_intervention.py
│   ├── weekly_reflection.py
│   └── goal_guardian.py
├── routers/                   # API endpoints
│   ├── auth.py
│   ├── profile.py
│   ├── analyze.py
│   ├── feedback.py
│   ├── balance.py
│   ├── debug.py
│   ├── metrics.py
│   └── experiments.py
├── services/                  # External integrations
│   ├── opik_service.py       # Opik observability
│   └── fdc_service.py        # USDA FDC integration
└── utils/                     # Utilities
    ├── confidence.py         # Confidence calculation
    └── emoji.py              # Status indicators

frontend/
├── src/
│   ├── App.jsx               # Main React component
│   ├── App.css               # Application styles
│   ├── api.js                # API client
│   ├── main.jsx              # React entry point
│   ├── index.css             # Global styles
│   ├── components/
│   │   ├── AgentInsights.jsx # Agent results display
│   │   └── MetricsDashboard.jsx
│   └── styles/
│       └── agent-insights.css
├── index.html
├── package.json
└── vite.config.js
```

## Key Features

**Multi-Agent Orchestration**: 10 specialized agents handle different aspects of meal analysis with clear separation of concerns.

**Opik Integration**: Full tracing of every agent decision for transparency and model improvement.

**Confidence Scoring**: Individual confidence per food item with overall confidence calculation and image ambiguity assessment.

**Daily Context**: Personalization agent considers previous meals today to determine energy balance status.

**Feedback Loop**: Users can correct analysis (portion size, wrong food) with feedback logged for model improvement.

**Weekly Reflection**: AI-powered insights on weekly patterns, goal alignment, and recommendations.

**Error Resilience**: Graceful fallbacks if individual agents fail; partial results returned rather than complete failure.

## License

MIT
