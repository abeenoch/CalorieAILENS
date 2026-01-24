import { useState, useEffect } from 'react';
import { exportsAPI } from '../api';

export function WeeklySummary() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [shareToken, setShareToken] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadSummary();
  }, []);

  async function loadSummary() {
    try {
      setLoading(true);
      const data = await exportsAPI.getWeeklySummary();
      setSummary(data);
    } catch (err) {
      console.error('Failed to load weekly summary:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleShare() {
    try {
      console.log('Share button clicked, calling API...');
      const result = await exportsAPI.createShareableWeeklySummary();
      console.log('Share API response:', result);
      setShareToken(result.share_token);
    } catch (err) {
      console.error('Failed to create shareable summary:', err);
      alert(`Error: ${err.message}`);
    }
  }

  function copyShareLink() {
    const link = `${window.location.origin}/exports/shared/${shareToken}`;
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (loading) {
    return <div className="loading-section"><div className="spinner"></div></div>;
  }

  if (!summary) {
    return <div className="empty-state">No data for this week yet</div>;
  }

  return (
    <div className="weekly-summary-container">
      <div className="summary-header">
        <h3>This Week's Wellness Summary</h3>
        <button className="btn btn-secondary btn-sm" onClick={handleShare}>
          {shareToken ? '✓ Shared' : '📤 Share'}
        </button>
      </div>

      <div className="summary-grid">
        <div className="summary-card">
          <span className="summary-label">Meals Logged</span>
          <span className="summary-value">{summary.meals_logged}</span>
        </div>
        <div className="summary-card">
          <span className="summary-label">Days Tracked</span>
          <span className="summary-value">{summary.days_tracked}/7</span>
        </div>
        <div className="summary-card">
          <span className="summary-label">Total Calories</span>
          <span className="summary-value">{Math.round(summary.total_calories)}</span>
        </div>
        <div className="summary-card">
          <span className="summary-label">Daily Average</span>
          <span className="summary-value">{Math.round(summary.average_calories_per_day)}</span>
        </div>
      </div>

      <div className="summary-macros">
        <h4>Macro Breakdown</h4>
        <div className="macro-breakdown">
          <div className="macro-item">
            <span className="macro-name">Protein</span>
            <span className="macro-value">{summary.macros.protein_g}g</span>
            <span className="macro-pct">{summary.macros.protein_pct}%</span>
          </div>
          <div className="macro-item">
            <span className="macro-name">Carbs</span>
            <span className="macro-value">{summary.macros.carbs_g}g</span>
            <span className="macro-pct">{summary.macros.carbs_pct}%</span>
          </div>
          <div className="macro-item">
            <span className="macro-name">Fat</span>
            <span className="macro-value">{summary.macros.fat_g}g</span>
            <span className="macro-pct">{summary.macros.fat_pct}%</span>
          </div>
        </div>
      </div>

      {summary.wellness_highlights && summary.wellness_highlights.length > 0 && (
        <div className="summary-insights">
          <h4>Wellness Highlights</h4>
          <ul className="insights-list">
            {summary.wellness_highlights.map((insight, i) => (
              <li key={i}>💡 {insight}</li>
            ))}
          </ul>
        </div>
      )}

      {shareToken && (
        <div className="share-section">
          <p className="share-label">Share this summary:</p>
          <div className="share-link-container">
            <input
              type="text"
              className="share-link-input"
              value={`${window.location.origin}/exports/shared/${shareToken}`}
              readOnly
            />
            <button className="btn btn-secondary btn-sm" onClick={copyShareLink}>
              {copied ? '✓ Copied' : '📋 Copy'}
            </button>
          </div>
          <p className="share-note">Anyone with this link can view your wellness summary (no personal data)</p>
        </div>
      )}
    </div>
  );
}
