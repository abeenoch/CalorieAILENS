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
- `GET /analyze/history` - Get meal history with filtering (date range, context, food search)
- `GET /analyze/meal/{id}` - Get detailed analysis for specific meal
- `GET /analyze/macros/today` - Get today's macro breakdown (for pie chart)
- `GET /analyze/macros/date-range` - Get macro breakdown for date range

### Feedback
- `POST /feedback` - Submit feedback for meal analysis
- `GET /feedback/meal/{id}` - Get feedback for specific meal
- `GET /feedback/stats` - Get feedback statistics

### Notifications
- `GET /notifications/preferences` - Get notification preferences
- `PUT /notifications/preferences` - Update notification preferences
- `GET /notifications/check-meal-reminder` - Check if meal reminder should be sent

### Exports & Sharing
- `GET /exports/weekly-summary` - Get this week's wellness summary
- `POST /exports/weekly-summary/share` - Create shareable weekly summary
- `GET /exports/shared/{share_token}` - View publicly shared summary (no auth required)

### Balance
- `GET /balance/today` - Today's energy balance summary
- `GET /balance/week` - Weekly balance breakdown
- `GET /balance/reflection/weekly` - AI-powered weekly reflection

## Database Schema

**Users**: Email, hashed password, profile ranges (age, height, weight, activity level, goal)

**Meals**: Image data, context, agent analysis results (stored as JSON), confidence scores

**Feedbacks**: Meal reference, feedback type (accurate/portion_bigger/portion_smaller/wrong_food), comment

**DailyBalances**: User reference, date, calorie ranges, balance status, reasoning

**NotificationPreferences**: User notification settings (meal reminders, weekly summaries, times)

**WeeklyExports**: Weekly summaries with shareable tokens for public viewing

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
3. Vision Interpreter detects if image contains a barcode
4. If barcode detected: Returns barcode number and suggests using `/analyze/barcode` endpoint
5. If regular food photo:
   - Vision Interpreter identifies foods and portions
   - Nutrition Reasoner calculates calorie ranges (queries USDA FDC, falls back to Open Food Facts)
   - Personalization Agent contextualizes with user profile and daily meals
   - Wellness Coach generates supportive feedback with safety checks
   - Advanced agents provide drift detection, next actions, strategy adaptation
6. All results logged to Opik with full trace
7. Results stored in database
8. Response sent to frontend with foods, calorie ranges, balance status, message, suggestions
9. User provides feedback (accurate/portion_bigger/etc.)
10. Feedback logged to Opik for model improvement

**Barcode Scanning**:
1. User uploads barcode image to `/analyze/meal`
2. Vision Interpreter detects barcode and returns barcode number
3. Frontend receives barcode number and calls `/analyze/barcode` endpoint
4. `/analyze/barcode` endpoint:
   - Queries Open Food Facts by barcode
   - Gets verified product name and nutrition data
   - Creates synthetic vision result with barcode data
   - Runs through personalization and wellness agents
   - Returns personalized analysis (balance status, supportive message)
   - Stores in database with full meal record
5. User gets same personalized experience as photo analysis

## Macro Aggregation & Visualization

The application provides macro aggregation endpoints for visualization:

**Today's Macros** (`GET /analyze/macros/today`):
```json
{
  "total_calories": 2150.5,
  "protein_g": 85.3,
  "carbs_g": 280.2,
  "fat_g": 65.1,
  "macro_percentages": {
    "protein": 16.5,
    "carbs": 54.2,
    "fat": 29.3
  },
  "meals_count": 3
}
```

**Date Range Macros** (`GET /analyze/macros/date-range?start_date=2025-01-20&end_date=2025-01-22`):
- Same response as today endpoint, plus:
  - `days_count`: Number of days in range
  - `average_calories_per_day`: Average daily calories

Macro percentages are calculated by calorie contribution:
- Protein: 4 calories per gram
- Carbs: 4 calories per gram
- Fat: 9 calories per gram

## Meal History Filtering

The `/analyze/history` endpoint now supports advanced filtering:

**Query Parameters**:
- `start_date` - Filter by start date (ISO format: YYYY-MM-DD)
- `end_date` - Filter by end date (ISO format: YYYY-MM-DD)
- `context` - Filter by meal context (homemade, restaurant, snack, meal)
- `food_name` - Search by food name (partial match, case-insensitive)
- `limit` - Number of results (default: 20)
- `offset` - Pagination offset (default: 0)

**Example**:
```bash
GET /analyze/history?start_date=2025-01-20&context=restaurant&food_name=chicken&limit=10
```

Returns meals from Jan 20 onwards, logged at restaurants, containing "chicken" in the food name.

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
│   ├── notifications.py       # Notification preferences
│   ├── exports.py             # Weekly summaries & sharing
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
│   │   ├── MacroChart.jsx    # Macro pie chart visualization
│   │   ├── NotificationSettings.jsx # Notification preferences
│   │   ├── WeeklySummary.jsx # Weekly summary & sharing
│   │   └── MetricsDashboard.jsx
│   └── styles/
│       ├── agent-insights.css
│       ├── macro-chart.css   # Macro chart styling
│       ├── history.css       # History view with filters
│       ├── home.css          # Home view macro details
│       └── notifications-exports.css # Notifications & exports styling
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

**Navigation**: The app includes intuitive navigation with dedicated pages for:
- **Home**: Daily energy balance and macro visualization
- **Analyze**: Photo/barcode scanning for meal analysis
- **History**: Meal history with advanced filtering and search
- **Notifications**: Manage meal reminders and weekly summaries
- **Share**: Create and share weekly wellness summaries
- **Profile**: Customize your wellness goals and preferences

## Recent Features

### Macro Visualization (Pie Chart)
- Donut pie chart showing protein/carbs/fat breakdown
- Color-coded macros: Protein (red), Carbs (teal), Fat (yellow)
- Displays on home page with total calories
- Macro percentages calculated by calorie contribution
- Responsive canvas-based rendering
- Endpoints: `/analyze/macros/today` and `/analyze/macros/date-range`

### Meal History with Search & Filtering
- Filter by date range (start_date, end_date)
- Filter by meal context (homemade, restaurant, snack, meal)
- Search by food name (case-insensitive partial match)
- Enhanced meal cards showing timestamp, macros, wellness message
- Collapsible filter panel with active filters display
- Pagination support for large meal histories

### Barcode Scanning
- Detect barcodes in food images automatically
- Query Open Food Facts database for product info
- Full agent pipeline for packaged foods (personalization + wellness)
- Support for EAN-13 and UPC-12 barcodes

### Notifications
- **Meal Reminders**: Optional daily reminders to log meals at a specific time
- **Weekly Summaries**: Automatic wellness summaries on a chosen day/time
- **Customizable**: Users can enable/disable and set preferred times
- **Endpoints**: Get/update preferences, check if reminder should be sent

**How to Use**:
1. Navigate to the **Notifications** page in the app
2. Toggle **Enable meal reminders** and set your preferred time
3. Toggle **Enable weekly summary** and choose your preferred day and time
4. Click **Save Preferences** to store your settings
5. Reminders will be checked when you visit the app at the scheduled times

### Exports & Sharing
- **Weekly Summaries**: Automatic aggregation of wellness data (meals, macros, insights)
- **Shareable Links**: Generate public links with unique tokens
- **Privacy-Focused**: Only shares high-level insights (meals logged, calories, macros, wellness highlights), not detailed tracking data
- **Public Access**: Anyone with the link can view (no authentication needed)
- **Unique Wellness Highlights**: Deduplicates wellness messages to show only unique insights
- **Production Ready**: URLs work across domains (e.g., `https://yourdomain.com/exports/shared/{token}`)
- **Endpoints**: Get summaries, create shares, view public summaries

**How to Use**:
1. Navigate to the **Share** page in the app
2. View your weekly wellness summary (meals logged, calories, macros, insights)
3. Click **Share** to generate a shareable link
4. Click **Copy** to copy the link to your clipboard
5. Share the link with anyone - they can view your wellness summary without logging in
6. The shared view displays only high-level insights, protecting your privacy

## License

MIT
