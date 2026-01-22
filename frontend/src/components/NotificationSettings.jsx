import { useState, useEffect } from 'react';
import { notificationsAPI } from '../api';

export function NotificationSettings() {
  const [preferences, setPreferences] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadPreferences();
  }, []);

  async function loadPreferences() {
    try {
      const data = await notificationsAPI.getPreferences();
      setPreferences(data);
    } catch (err) {
      console.error('Failed to load notification preferences:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    try {
      await notificationsAPI.updatePreferences(preferences);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save preferences:', err);
    }
  }

  if (loading) {
    return <div className="loading-section"><div className="spinner"></div></div>;
  }

  if (!preferences) {
    return <div className="empty-state">Failed to load preferences</div>;
  }

  return (
    <div className="notification-settings">
      <h3>Notification Preferences</h3>

      <div className="settings-section">
        <div className="setting-group">
          <label className="setting-label">
            <input
              type="checkbox"
              checked={preferences.meal_reminders_enabled}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  meal_reminders_enabled: e.target.checked,
                })
              }
            />
            <span>Enable meal reminders</span>
          </label>
          {preferences.meal_reminders_enabled && (
            <div className="setting-input">
              <label>Reminder time:</label>
              <input
                type="time"
                value={preferences.meal_reminder_time || '12:00'}
                onChange={(e) =>
                  setPreferences({
                    ...preferences,
                    meal_reminder_time: e.target.value,
                  })
                }
              />
            </div>
          )}
        </div>

        <div className="setting-group">
          <label className="setting-label">
            <input
              type="checkbox"
              checked={preferences.weekly_summary_enabled}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  weekly_summary_enabled: e.target.checked,
                })
              }
            />
            <span>Enable weekly summary</span>
          </label>
          {preferences.weekly_summary_enabled && (
            <div className="setting-inputs">
              <div className="setting-input">
                <label>Day:</label>
                <select
                  value={preferences.weekly_summary_day || 'sunday'}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      weekly_summary_day: e.target.value,
                    })
                  }
                >
                  <option value="monday">Monday</option>
                  <option value="tuesday">Tuesday</option>
                  <option value="wednesday">Wednesday</option>
                  <option value="thursday">Thursday</option>
                  <option value="friday">Friday</option>
                  <option value="saturday">Saturday</option>
                  <option value="sunday">Sunday</option>
                </select>
              </div>
              <div className="setting-input">
                <label>Time:</label>
                <input
                  type="time"
                  value={preferences.weekly_summary_time || '19:00'}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      weekly_summary_time: e.target.value,
                    })
                  }
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {saved && <div className="success-message">✅ Preferences saved!</div>}

      <button className="btn btn-primary" onClick={handleSave}>
        Save Preferences
      </button>
    </div>
  );
}
