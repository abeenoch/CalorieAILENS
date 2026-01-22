import { useState, useEffect, createContext, useContext } from 'react';
import './App.css';
import './styles/agent-insights.css';
import './styles/macro-chart.css';
import './styles/history.css';
import './styles/home.css';
import './styles/notifications-exports.css';
import { authAPI, profileAPI, analyzeAPI, balanceAPI, feedbackAPI } from './api';
import { MacroChart } from './components/MacroChart';
import { NotificationSettings } from './components/NotificationSettings';
import { WeeklySummary } from './components/WeeklySummary';

// Auth Context
const AuthContext = createContext(null);

function useAuth() {
  return useContext(AuthContext);
}

// Main App Component
function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentView, setCurrentView] = useState('home');
  const [sharedSummary, setSharedSummary] = useState(null);

  useEffect(() => {
    checkAuth();
    // Check if we're viewing a shared summary
    const path = window.location.pathname;
    if (path.startsWith('/exports/shared/')) {
      const shareToken = path.split('/').pop();
      loadSharedSummary(shareToken);
    }
  }, []);

  async function loadSharedSummary(shareToken) {
    try {
      const data = await analyzeAPI.getSharedSummary(shareToken);
      setSharedSummary(data);
      setCurrentView('shared-summary');
    } catch (err) {
      console.error('Failed to load shared summary:', err);
    }
  }

  async function checkAuth() {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const userData = await authAPI.getMe();
        setUser(userData);
      } catch {
        localStorage.removeItem('token');
      }
    }
    setLoading(false);
  }

  function handleLogin(userData, token) {
    localStorage.setItem('token', token);
    setUser(userData);
    // Redirect to profile if first-time user (no profile data set)
    const isFirstTimeUser = !userData.age_range && !userData.height_range && !userData.weight_range;
    setCurrentView(isFirstTimeUser ? 'profile' : 'home');
  }

  function handleLogout() {
    localStorage.removeItem('token');
    setUser(null);
    setCurrentView('home');
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, setUser, handleLogout }}>
      <div className="app">
        <Header
          user={user}
          currentView={currentView}
          setCurrentView={setCurrentView}
          onLogout={handleLogout}
        />

        <main className="main-content">
          <Disclaimer />

          {sharedSummary ? (
            <SharedSummaryView summary={sharedSummary} />
          ) : !user ? (
            <AuthView onLogin={handleLogin} />
          ) : (
            <>
              {currentView === 'home' && <HomeView setCurrentView={setCurrentView} />}
              {currentView === 'analyze' && <AnalyzeView />}
              {currentView === 'profile' && <ProfileView />}
              {currentView === 'history' && <HistoryView />}
              {currentView === 'notifications' && <NotificationsView />}
              {currentView === 'exports' && <ExportsView />}
            </>
          )}
        </main>
      </div>
    </AuthContext.Provider>
  );
}

// Header Component
function Header({ user, currentView, setCurrentView, onLogout }) {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo" onClick={() => setCurrentView('home')}>
          <span className="logo-icon">🍎</span>
          <span className="logo-text">Calorie Tracker</span>
        </div>

        {user && (
          <nav className="nav">
            <button
              className={`nav-link ${currentView === 'home' ? 'active' : ''}`}
              onClick={() => setCurrentView('home')}
            >
              Home
            </button>
            <button
              className={`nav-link ${currentView === 'analyze' ? 'active' : ''}`}
              onClick={() => setCurrentView('analyze')}
            >
              📷 Analyze
            </button>
            <button
              className={`nav-link ${currentView === 'history' ? 'active' : ''}`}
              onClick={() => setCurrentView('history')}
            >
              History
            </button>
            <button
              className={`nav-link ${currentView === 'notifications' ? 'active' : ''}`}
              onClick={() => setCurrentView('notifications')}
            >
              🔔 Notifications
            </button>
            <button
              className={`nav-link ${currentView === 'exports' ? 'active' : ''}`}
              onClick={() => setCurrentView('exports')}
            >
              📤 Share
            </button>
            <button
              className={`nav-link ${currentView === 'profile' ? 'active' : ''}`}
              onClick={() => setCurrentView('profile')}
            >
              Profile
            </button>
            <button className="nav-link logout" onClick={onLogout}>
              Logout
            </button>
          </nav>
        )}
      </div>
    </header>
  );
}

// Disclaimer Component
function Disclaimer() {
  return (
    <div className="disclaimer-banner">
      ℹ️ This app provides general wellness insights, not medical advice.
    </div>
  );
}

// Auth View (Login/Register)
function AuthView({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        const tokenData = await authAPI.login(email, password);
        localStorage.setItem('token', tokenData.access_token);
        const userData = await authAPI.getMe();
        onLogin(userData, tokenData.access_token);
      } else {
        await authAPI.register(email, password);
        const tokenData = await authAPI.login(email, password);
        localStorage.setItem('token', tokenData.access_token);
        const userData = await authAPI.getMe();
        onLogin(userData, tokenData.access_token);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-view">
      <div className="auth-card card">
        <div className="auth-header">
          <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
          <p className="text-muted">
            {isLogin
              ? 'Log in to track your meals'
              : 'Start your wellness journey'}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              type="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              minLength={6}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-lg w-full"
            disabled={loading}
          >
            {loading ? 'Please wait...' : (isLogin ? 'Log In' : 'Sign Up')}
          </button>
        </form>

        <div className="auth-switch">
          <button
            className="btn btn-ghost"
            onClick={() => setIsLogin(!isLogin)}
          >
            {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Log in'}
          </button>
        </div>
      </div>
    </div>
  );
}

// Home View
function HomeView({ setCurrentView }) {
  const { user } = useAuth();
  const [balance, setBalance] = useState(null);
  const [macros, setMacros] = useState(null);

  useEffect(() => {
    loadBalance();
    loadMacros();
  }, []);

  async function loadBalance() {
    try {
      const data = await balanceAPI.getToday();
      setBalance(data);
    } catch (err) {
      console.error('Failed to load balance:', err);
    }
  }

  async function loadMacros() {
    try {
      const data = await analyzeAPI.getTodayMacros();
      setMacros(data);
    } catch (err) {
      console.error('Failed to load macros:', err);
    }
  }

  const getStatusClass = (status) => {
    switch (status) {
      case 'under_fueled': return 'status-under';
      case 'roughly_aligned': return 'status-aligned';
      case 'slightly_over': return 'status-over';
      default: return 'status-aligned';
    }
  };

  return (
    <div className="home-view animate-fade-in">
      <div className="welcome-section">
        <h1>Hello{user?.email ? `, ${user.email.split('@')[0]}` : ''}! 👋</h1>
        <p className="text-muted">Track your meals and maintain your energy balance.</p>
      </div>

      {balance && (
        <div className="balance-card card">
          <div className="balance-header">
            <h3>Today's Energy Balance</h3>
            <span className={`status-badge ${getStatusClass(balance.balance_status)}`}>
              {balance.emoji_indicator} {balance.balance_status?.replace('_', ' ')}
            </span>
          </div>

          <div className="balance-stats">
            <div className="stat">
              <span className="stat-value">
                {balance.total_calories_min}-{balance.total_calories_max}
              </span>
              <span className="stat-label">Calories (est.)</span>
            </div>
            <div className="stat">
              <span className="stat-value">{balance.meals_count}</span>
              <span className="stat-label">Meals Logged</span>
            </div>
          </div>

          <p className="balance-reasoning">{balance.reasoning}</p>
        </div>
      )}

      {macros && (
        <div className="card">
          <h3>Today's Macros</h3>
          <MacroChart macros={macros} totalCalories={macros.total_calories} />
          <div className="macro-details">
            <div className="macro-detail-item">
              <span className="macro-detail-label">Protein</span>
              <span className="macro-detail-value">{macros.protein_g}g</span>
            </div>
            <div className="macro-detail-item">
              <span className="macro-detail-label">Carbs</span>
              <span className="macro-detail-value">{macros.carbs_g}g</span>
            </div>
            <div className="macro-detail-item">
              <span className="macro-detail-label">Fat</span>
              <span className="macro-detail-value">{macros.fat_g}g</span>
            </div>
          </div>
        </div>
      )}

      <div className="action-cards">
        <div className="action-card card" onClick={() => setCurrentView('analyze')}>
          <span className="action-icon">📷</span>
          <h4>Analyze Meal</h4>
          <p>Snap a photo to get instant nutrition insights</p>
        </div>

        <div className="action-card card" onClick={() => setCurrentView('history')}>
          <span className="action-icon">📊</span>
          <h4>View History</h4>
          <p>Review your past meals and patterns</p>
        </div>

        <div className="action-card card" onClick={() => setCurrentView('profile')}>
          <span className="action-icon">⚙️</span>
          <h4>Update Profile</h4>
          <p>Personalize your recommendations</p>
        </div>
      </div>
    </div>
  );
}

// Analyze View
function AnalyzeView() {
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [context, setContext] = useState('');
  const [notes, setNotes] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  function handleImageChange(e) {
    const file = e.target.files[0];
    if (file) {
      setImage(file);
      setImagePreview(URL.createObjectURL(file));
      setResult(null);
      setError('');
    }
  }

  async function handleAnalyze() {
    if (!image) return;

    setAnalyzing(true);
    setError('');

    try {
      // Convert image to base64
      const base64 = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64String = reader.result.split(',')[1];
          resolve(base64String);
        };
        reader.readAsDataURL(image);
      });

      const data = await analyzeAPI.analyzeMeal(
        base64,
        image.type,
        context || null,
        notes || null
      );

      // Check if barcode was detected in the image
      if (data.vision?.barcode_detected) {
        console.log('Barcode detected:', data.vision.barcode_detected);
        // Call the barcode endpoint for full agent analysis
        try {
          const barcodeData = await analyzeAPI.scanBarcode(
            data.vision.barcode_detected,
            context || null,
            notes || null
          );
          setResult(barcodeData);
        } catch (barcodeErr) {
          // If barcode lookup fails, show the error but allow user to continue
          setError(`Barcode scan failed: ${barcodeErr.message}. Try uploading a food photo instead.`);
          // Still show the meal analysis result if available
          setResult(data);
        }
      } else {
        setResult(data);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  function resetForm() {
    setImage(null);
    setImagePreview(null);
    setContext('');
    setNotes('');
    setResult(null);
    setError('');
  }

  return (
    <div className="analyze-view animate-fade-in">
      <h2>Analyze Your Meal 📷</h2>

      {!result ? (
        <div className="upload-section card">
          <div className="image-upload">
            {imagePreview ? (
              <div className="image-preview">
                <img src={imagePreview} alt="Meal preview" />
                <button className="btn btn-ghost btn-sm" onClick={resetForm}>
                  Remove
                </button>
              </div>
            ) : (
              <label className="upload-area">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageChange}
                  capture="environment"
                />
                <span className="upload-icon">📷</span>
                <span>Click to upload or take a photo</span>
              </label>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">Meal Context (optional)</label>
            <select
              className="form-select"
              value={context}
              onChange={(e) => setContext(e.target.value)}
            >
              <option value="">Select context...</option>
              <option value="homemade">🏠 Homemade</option>
              <option value="restaurant">🍽️ Restaurant</option>
              <option value="snack">🍿 Snack</option>
              <option value="meal">🍱 Full Meal</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Notes (optional)</label>
            <input
              type="text"
              className="form-input"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any additional notes..."
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button
            className="btn btn-primary btn-lg w-full"
            onClick={handleAnalyze}
            disabled={!image || analyzing}
          >
            {analyzing ? (
              <>
                <span className="spinner" style={{ width: 20, height: 20 }}></span>
                Analyzing with AI...
              </>
            ) : (
              '✨ Analyze Meal'
            )}
          </button>
        </div>
      ) : (
        <AnalysisResult result={result} onReset={resetForm} />
      )}
    </div>
  );
}

// Analysis Result Component
function AnalysisResult({ result, onReset }) {
  const [feedbackSent, setFeedbackSent] = useState(false);

  async function sendFeedback(type) {
    try {
      await feedbackAPI.create(result.meal_id, type);
      setFeedbackSent(true);
    } catch (err) {
      console.error('Failed to send feedback:', err);
    }
  }

  const getStatusClass = (status) => {
    switch (status) {
      case 'under_fueled': return 'status-under';
      case 'roughly_aligned': return 'status-aligned';
      case 'slightly_over': return 'status-over';
      default: return 'status-aligned';
    }
  };

  return (
    <div className="analysis-result animate-fade-in">
      {/* Wellness Message */}
      <div className="wellness-card card">
        <div className="wellness-emoji">{result.wellness.emoji_indicator}</div>
        <p className="wellness-message">{result.wellness.message}</p>
        {result.wellness.suggestions?.length > 0 && (
          <ul className="wellness-suggestions">
            {result.wellness.suggestions.map((s, i) => (
              <li key={i}>💡 {s}</li>
            ))}
          </ul>
        )}
      </div>

      {/* Foods Identified */}
      <div className="card">
        <h4>🍽️ Foods Identified</h4>
        <div className="foods-list">
          {result.vision.foods.map((food, i) => (
            <div key={i} className="food-item">
              <span className="food-name">{food.name}</span>
              <span className="food-portion">{food.portion}</span>
              <span className={`confidence-badge confidence-${food.confidence}`}>
                {food.confidence}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Nutrition Estimates */}
      <div className="card">
        <h4>📊 Nutrition Estimates</h4>
        <div className="nutrition-stats">
          <div className="nutrition-stat">
            <span className="stat-label">Calories</span>
            <span className="stat-value">
              {result.nutrition.total_calories.min} - {result.nutrition.total_calories.max}
            </span>
          </div>
          <div className="macros-row">
            <div className="macro">
              <span className="macro-label">Protein</span>
              <span className="macro-value">{result.nutrition.macros.protein}</span>
            </div>
            <div className="macro">
              <span className="macro-label">Carbs</span>
              <span className="macro-value">{result.nutrition.macros.carbs}</span>
            </div>
            <div className="macro">
              <span className="macro-label">Fat</span>
              <span className="macro-value">{result.nutrition.macros.fat}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Balance Status */}
      <div className="card">
        <h4>⚖️ Energy Balance</h4>
        <span className={`status-badge ${getStatusClass(result.personalization.balance_status)}`}>
          {result.wellness.emoji_indicator} {result.personalization.balance_status?.replace('_', ' ')}
        </span>
        <p className="mt-md text-muted">{result.personalization.daily_context}</p>
      </div>

      {/* Feedback */}
      <div className="card feedback-card">
        <h4>Was this analysis accurate?</h4>
        {!feedbackSent ? (
          <div className="feedback-buttons">
            <button className="btn btn-secondary" onClick={() => sendFeedback('accurate')}>
              ✅ Accurate
            </button>
            <button className="btn btn-secondary" onClick={() => sendFeedback('portion_bigger')}>
              ⬆️ Portion was bigger
            </button>
            <button className="btn btn-secondary" onClick={() => sendFeedback('portion_smaller')}>
              ⬇️ Portion was smaller
            </button>
          </div>
        ) : (
          <p className="feedback-thanks">Thanks for your feedback! 🙏</p>
        )}
      </div>

      <button className="btn btn-primary btn-lg w-full" onClick={onReset}>
        Analyze Another Meal
      </button>
    </div>
  );
}

// Profile View
function ProfileView() {
  const { user, setUser } = useAuth();
  const [options, setOptions] = useState(null);
  const [useCustomGoal, setUseCustomGoal] = useState(false);
  const [form, setForm] = useState({
    age_range: user?.age_range || '',
    height_range: user?.height_range || '',
    weight_range: user?.weight_range || '',
    activity_level: user?.activity_level || '',
    goal: user?.goal || '',
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadOptions();
    // Check if goal is custom (not in predefined list)
    if (user?.goal && options?.goals && !options.goals.find(g => g.value === user.goal)) {
      setUseCustomGoal(true);
    }
  }, []);

  async function loadOptions() {
    try {
      const data = await profileAPI.getOptions();
      setOptions(data);
    } catch (err) {
      console.error('Failed to load options:', err);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      const updated = await profileAPI.update(form);
      setUser(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save:', err);
    } finally {
      setSaving(false);
    }
  }

  if (!options) {
    return (
      <div className="loading-section">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="profile-view animate-fade-in">
      <div className="profile-header">
        <h2>Your Profile ⚙️</h2>
        <p className="text-muted">
          Personalize your recommendations. All fields use ranges for privacy.
        </p>
      </div>

      <div className="card profile-card">
        <div className="form-group">
          <label className="form-label">Age Range</label>
          <select
            className="form-select"
            value={form.age_range}
            onChange={(e) => setForm({ ...form, age_range: e.target.value })}
          >
            <option value="">Select your age range...</option>
            {options.age_ranges.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Height Range</label>
          <select
            className="form-select"
            value={form.height_range}
            onChange={(e) => setForm({ ...form, height_range: e.target.value })}
          >
            <option value="">Select your height range...</option>
            {options.height_ranges.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Weight Range</label>
          <select
            className="form-select"
            value={form.weight_range}
            onChange={(e) => setForm({ ...form, weight_range: e.target.value })}
          >
            <option value="">Select your weight range...</option>
            {options.weight_ranges.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Activity Level</label>
          <select
            className="form-select"
            value={form.activity_level}
            onChange={(e) => setForm({ ...form, activity_level: e.target.value })}
          >
            <option value="">Select your activity level...</option>
            {options.activity_levels.map(o => (
              <option key={o.value} value={o.value}>{o.description}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Wellness Goal</label>
          <div className="goal-input-wrapper">
            {!useCustomGoal ? (
              <>
                <select
                  className="form-select"
                  value={form.goal}
                  onChange={(e) => {
                    if (e.target.value === '__custom__') {
                      setUseCustomGoal(true);
                      setForm({ ...form, goal: '' });
                    } else {
                      setForm({ ...form, goal: e.target.value });
                    }
                  }}
                >
                  <option value="">Select a goal...</option>
                  {options.goals.map(o => (
                    <option key={o.value} value={o.value}>{o.description}</option>
                  ))}
                  <option value="__custom__">✏️ Enter custom goal</option>
                </select>
              </>
            ) : (
              <>
                <input
                  type="text"
                  className="form-input"
                  value={form.goal}
                  onChange={(e) => setForm({ ...form, goal: e.target.value })}
                  placeholder="e.g., Build muscle, Increase energy, etc."
                />
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => {
                    setUseCustomGoal(false);
                    setForm({ ...form, goal: '' });
                  }}
                >
                  Back to options
                </button>
              </>
            )}
          </div>
        </div>

        {saved && <div className="success-message">✅ Profile saved successfully!</div>}

        <button
          className="btn btn-primary btn-lg w-full"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : '💾 Save Profile'}
        </button>
      </div>
    </div>
  );
}

// History View
function HistoryView() {
  const [meals, setMeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    context: '',
    foodName: '',
  });
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    try {
      setLoading(true);
      const data = await analyzeAPI.getHistory(20, 0, filters);
      setMeals(data);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  }

  function handleFilterChange(field, value) {
    setFilters(prev => ({ ...prev, [field]: value }));
  }

  function handleApplyFilters() {
    loadHistory();
    setShowFilters(false);
  }

  function handleClearFilters() {
    setFilters({
      startDate: '',
      endDate: '',
      context: '',
      foodName: '',
    });
  }

  if (loading && meals.length === 0) {
    return (
      <div className="loading-section">
        <div className="spinner"></div>
      </div>
    );
  }

  const hasActiveFilters = Object.values(filters).some(v => v);

  return (
    <div className="history-view animate-fade-in">
      <div className="history-header">
        <h2>Meal History 📊</h2>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => setShowFilters(!showFilters)}
        >
          {showFilters ? '✕ Close' : '🔍 Filter'}
        </button>
      </div>

      {showFilters && (
        <div className="filter-panel card">
          <div className="filter-group">
            <label className="form-label">Start Date</label>
            <input
              type="date"
              className="form-input"
              value={filters.startDate}
              onChange={(e) => handleFilterChange('startDate', e.target.value)}
            />
          </div>

          <div className="filter-group">
            <label className="form-label">End Date</label>
            <input
              type="date"
              className="form-input"
              value={filters.endDate}
              onChange={(e) => handleFilterChange('endDate', e.target.value)}
            />
          </div>

          <div className="filter-group">
            <label className="form-label">Meal Context</label>
            <select
              className="form-select"
              value={filters.context}
              onChange={(e) => handleFilterChange('context', e.target.value)}
            >
              <option value="">All contexts</option>
              <option value="homemade">🏠 Homemade</option>
              <option value="restaurant">🍽️ Restaurant</option>
              <option value="snack">🍿 Snack</option>
              <option value="meal">🍱 Full Meal</option>
            </select>
          </div>

          <div className="filter-group">
            <label className="form-label">Search Food</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g., chicken, salad..."
              value={filters.foodName}
              onChange={(e) => handleFilterChange('foodName', e.target.value)}
            />
          </div>

          <div className="filter-actions">
            <button className="btn btn-primary" onClick={handleApplyFilters}>
              Apply Filters
            </button>
            {hasActiveFilters && (
              <button className="btn btn-ghost" onClick={handleClearFilters}>
                Clear All
              </button>
            )}
          </div>
        </div>
      )}

      {hasActiveFilters && (
        <div className="active-filters">
          {filters.startDate && <span className="filter-tag">From {filters.startDate}</span>}
          {filters.endDate && <span className="filter-tag">To {filters.endDate}</span>}
          {filters.context && <span className="filter-tag">Context: {filters.context}</span>}
          {filters.foodName && <span className="filter-tag">Search: {filters.foodName}</span>}
        </div>
      )}

      {meals.length === 0 ? (
        <div className="empty-state card">
          <span className="empty-icon">🍽️</span>
          <p>{hasActiveFilters ? 'No meals match your filters.' : 'No meals logged yet. Start by analyzing a meal!'}</p>
        </div>
      ) : (
        <div className="meals-list">
          {meals.map(meal => (
            <div key={meal.id} className="meal-card card">
              <div className="meal-header">
                <span className="meal-context">{meal.context || 'Meal'}</span>
                <span className="meal-date">
                  {new Date(meal.created_at).toLocaleDateString()} {new Date(meal.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>

              <div className="meal-foods">
                {meal.vision_result?.foods?.slice(0, 3).map((f, i) => (
                  <span key={i} className="food-tag">{f.name}</span>
                ))}
              </div>

              <div className="meal-nutrition">
                <div className="nutrition-item">
                  <span className="nutrition-label">Calories</span>
                  <span className="nutrition-value">
                    {meal.nutrition_result?.total_calories?.min || 0} -
                    {meal.nutrition_result?.total_calories?.max || 0} kcal
                  </span>
                </div>
                <div className="nutrition-item">
                  <span className="nutrition-label">Macros</span>
                  <span className="nutrition-value">
                    P: {meal.nutrition_result?.macros?.protein || 'N/A'} |
                    C: {meal.nutrition_result?.macros?.carbs || 'N/A'} |
                    F: {meal.nutrition_result?.macros?.fat || 'N/A'}
                  </span>
                </div>
              </div>

              {meal.wellness_result?.message && (
                <div className="meal-message">
                  {meal.wellness_result.emoji_indicator} {meal.wellness_result.message}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Notifications View
function NotificationsView() {
  return (
    <div className="notifications-view animate-fade-in">
      <div className="view-header">
        <h2>Notification Settings 🔔</h2>
        <p className="text-muted">Manage your meal reminders and weekly summaries</p>
      </div>
      <div className="card">
        <NotificationSettings />
      </div>
    </div>
  );
}

// Exports View
function ExportsView() {
  return (
    <div className="exports-view animate-fade-in">
      <div className="view-header">
        <h2>Share Your Wellness 📤</h2>
        <p className="text-muted">Share your weekly wellness summary with others</p>
      </div>
      <div className="card">
        <WeeklySummary />
      </div>
    </div>
  );
}

// Shared Summary View (Public)
function SharedSummaryView({ summary }) {
  if (!summary) {
    return (
      <div className="loading-section">
        <div className="spinner"></div>
      </div>
    );
  }

  const data = summary.summary;

  return (
    <div className="shared-summary-view animate-fade-in">
      <div className="view-header">
        <h2>Wellness Summary 🌟</h2>
        <p className="text-muted">Week of {new Date(data.week_start).toLocaleDateString()}</p>
      </div>

      <div className="card">
        <div className="summary-grid">
          <div className="summary-card">
            <span className="summary-label">Meals Logged</span>
            <span className="summary-value">{data.meals_logged}</span>
          </div>
          <div className="summary-card">
            <span className="summary-label">Days Tracked</span>
            <span className="summary-value">{data.days_tracked}/7</span>
          </div>
          <div className="summary-card">
            <span className="summary-label">Total Calories</span>
            <span className="summary-value">{Math.round(data.total_calories)}</span>
          </div>
          <div className="summary-card">
            <span className="summary-label">Daily Average</span>
            <span className="summary-value">{Math.round(data.average_calories_per_day)}</span>
          </div>
        </div>
      </div>

      <div className="card">
        <h4>Macro Breakdown</h4>
        <div className="macro-breakdown">
          <div className="macro-item">
            <span className="macro-name">Protein</span>
            <span className="macro-value">{data.macros.protein_g}g</span>
            <span className="macro-pct">{data.macros.protein_pct}%</span>
          </div>
          <div className="macro-item">
            <span className="macro-name">Carbs</span>
            <span className="macro-value">{data.macros.carbs_g}g</span>
            <span className="macro-pct">{data.macros.carbs_pct}%</span>
          </div>
          <div className="macro-item">
            <span className="macro-name">Fat</span>
            <span className="macro-value">{data.macros.fat_g}g</span>
            <span className="macro-pct">{data.macros.fat_pct}%</span>
          </div>
        </div>
      </div>

      {data.wellness_highlights && data.wellness_highlights.length > 0 && (
        <div className="card">
          <h4>Wellness Highlights</h4>
          <ul className="insights-list">
            {data.wellness_highlights.map((insight, i) => (
              <li key={i}>💡 {insight}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="card" style={{ textAlign: 'center', color: '#666' }}>
        <p>✨ This is a shared wellness summary. No personal data is included.</p>
      </div>
    </div>
  );
}

export default App;
