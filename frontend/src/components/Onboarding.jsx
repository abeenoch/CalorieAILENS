import { useState, useEffect } from 'react';
import { profileAPI } from '../api';

export function Onboarding({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [options, setOptions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    gender: '',
    age_range: '',
    height_range: '',
    weight_range: '',
    activity_level: '',
    goal: '',
  });
  const [saving, setSaving] = useState(false);
  const [heightUnit, setHeightUnit] = useState('ft');
  const [customGoal, setCustomGoal] = useState('');
  const [useCustomGoal, setUseCustomGoal] = useState(false);

  const heightRanges = [
    { label: "under 150cm", value: "under 150cm", min: 0, max: 150 },
    { label: "150-160cm", value: "150-160cm", min: 150, max: 160 },
    { label: "160-170cm", value: "160-170cm", min: 160, max: 170 },
    { label: "170-180cm", value: "170-180cm", min: 170, max: 180 },
    { label: "180-190cm", value: "180-190cm", min: 180, max: 190 },
    { label: "over 190cm", value: "over 190cm", min: 190, max: 300 },
  ];

  useEffect(() => {
    loadOptions();
  }, []);

  async function loadOptions() {
    try {
      const data = await profileAPI.getOptions();
      setOptions(data);
      setLoading(false);
    } catch (err) {
      console.error('Failed to load options:', err);
      setLoading(false);
    }
  }

  function convertHeightToCm(feet, inches) {
    return Math.round(feet * 30.48 + inches * 2.54);
  }

  function getHeightRangeFromCm(cm) {
    for (let range of heightRanges) {
      if (cm >= range.min && cm <= range.max) {
        return range.value;
      }
    }
    return heightRanges[heightRanges.length - 1].value;
  }

  const steps = [
    {
      title: 'Gender',
      description: 'Help us personalize your experience',
      field: 'gender',
      type: 'grid',
      options: [
        { value: 'male', label: 'Male', icon: '👨' },
        { value: 'female', label: 'Female', icon: '👩' },
        { value: 'other', label: 'Other', icon: '🧑' },
      ],
    },
    {
      title: 'Age Range',
      description: 'Help us understand your life stage',
      field: 'age_range',
      type: 'grid',
      options: options?.age_ranges?.map(r => ({
        value: r,
        label: r,
        icon: getAgeIcon(r),
      })) || [],
    },
    {
      title: 'Height',
      description: 'Select your height range',
      field: 'height_range',
      type: 'height',
    },
    {
      title: 'Weight Range',
      description: 'Select your weight range',
      field: 'weight_range',
      type: 'grid',
      options: options?.weight_ranges?.map(r => ({
        value: r,
        label: r,
        icon: getWeightIcon(r),
      })) || [],
    },
    {
      title: 'Activity Level',
      description: 'How active are you?',
      field: 'activity_level',
      type: 'grid',
      options: options?.activity_levels?.map(o => ({
        value: o.value,
        label: o.description,
        icon: getActivityIcon(o.value),
      })) || [],
    },
    {
      title: 'Wellness Goal',
      description: 'What is your main wellness goal?',
      field: 'goal',
      type: 'goal',
      options: options?.goals?.map(o => ({
        value: o.value,
        label: o.description,
        icon: getGoalIcon(o.value),
      })) || [],
    },
  ];

  const currentStepData = steps[currentStep];
  const isLastStep = currentStep === steps.length - 1;

  let isStepComplete = false;
  if (currentStepData?.type === 'height') {
    isStepComplete = form.height_range !== '';
  } else if (currentStepData?.type === 'goal') {
    isStepComplete = form.goal !== '' || customGoal !== '';
  } else {
    isStepComplete = form[currentStepData?.field] !== '';
  }

  async function handleNext() {
    if (isLastStep) {
      await handleComplete();
    } else {
      setCurrentStep(currentStep + 1);
    }
  }

  async function handleComplete() {
    setSaving(true);
    try {
      const finalForm = {
        ...form,
        goal: customGoal || form.goal,
      };

      const updated = await profileAPI.update(finalForm);
      onComplete(updated);
    } catch (err) {
      console.error('Failed to save profile:', err);
      setSaving(false);
    }
  }

  function handleSelect(value) {
    setForm({ ...form, [currentStepData.field]: value });
  }

  if (loading) {
    return (
      <div className="onboarding-container">
        <div className="onboarding-card">
          <div style={{ textAlign: 'center' }}>
            <div className="spinner"></div>
            <p style={{ marginTop: '16px', color: '#6b7280' }}>Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  const progress = ((currentStep + 1) / steps.length) * 100;

  return (
    <div className="onboarding-container">
      <div className="onboarding-card">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }}></div>
        </div>

        <div className="onboarding-header">
          <h2>{currentStepData.title}</h2>
          <p>{currentStepData.description}</p>
        </div>

        {currentStepData.type === 'grid' && (
          <div className={currentStepData.options.length > 4 ? 'options-grid' : 'two-column-grid'}>
            {currentStepData.options.map(option => (
              <button
                key={option.value}
                className={`option-button ${form[currentStepData.field] === option.value ? 'selected' : ''}`}
                onClick={() => handleSelect(option.value)}
              >
                <div className="option-icon">{option.icon}</div>
                <div className="option-text">
                  <div className="option-label">{option.label}</div>
                </div>
              </button>
            ))}
          </div>
        )}

        {currentStepData.type === 'height' && (
          <div>
            <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
              <button
                className={`option-button ${heightUnit === 'ft' ? 'selected' : ''}`}
                onClick={() => setHeightUnit('ft')}
                style={{ flex: 1 }}
              >
                <div className="option-label">Feet & Inches</div>
              </button>
              <button
                className={`option-button ${heightUnit === 'cm' ? 'selected' : ''}`}
                onClick={() => setHeightUnit('cm')}
                style={{ flex: 1 }}
              >
                <div className="option-label">Centimeters</div>
              </button>
            </div>

            {heightUnit === 'ft' ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '600', color: '#374151' }}>
                    Feet
                  </label>
                  <input
                    type="number"
                    min="4"
                    max="7"
                    placeholder="e.g., 5"
                    id="feet-input"
                    style={{
                      width: '100%',
                      padding: '12px',
                      border: '2px solid #e5e7eb',
                      borderRadius: '8px',
                      fontSize: '16px',
                    }}
                    onChange={(e) => {
                      const feet = parseInt(e.target.value) || 0;
                      const inchesInput = document.querySelector('#inches-input');
                      const inches = parseInt(inchesInput?.value) || 0;
                      if (feet > 0) {
                        const cm = convertHeightToCm(feet, inches);
                        const range = getHeightRangeFromCm(cm);
                        setForm({ ...form, height_range: range });
                      }
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '600', color: '#374151' }}>
                    Inches
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="11"
                    placeholder="e.g., 10"
                    id="inches-input"
                    style={{
                      width: '100%',
                      padding: '12px',
                      border: '2px solid #e5e7eb',
                      borderRadius: '8px',
                      fontSize: '16px',
                    }}
                    onChange={(e) => {
                      const feetInput = document.querySelector('#feet-input');
                      const feet = parseInt(feetInput?.value) || 0;
                      const inches = parseInt(e.target.value) || 0;
                      if (feet > 0) {
                        const cm = convertHeightToCm(feet, inches);
                        const range = getHeightRangeFromCm(cm);
                        setForm({ ...form, height_range: range });
                      }
                    }}
                  />
                </div>
              </div>
            ) : (
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '600', color: '#374151' }}>
                  Height (cm)
                </label>
                <input
                  type="number"
                  min="120"
                  max="220"
                  placeholder="e.g., 175"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '16px',
                  }}
                  onChange={(e) => {
                    const cm = parseInt(e.target.value) || 0;
                    if (cm > 0) {
                      const range = getHeightRangeFromCm(cm);
                      setForm({ ...form, height_range: range });
                    }
                  }}
                />
              </div>
            )}
          </div>
        )}

        {currentStepData.type === 'goal' && (
          <div>
            <div className="two-column-grid" style={{ marginBottom: '20px' }}>
              {currentStepData.options.map(option => (
                <button
                  key={option.value}
                  className={`option-button ${form.goal === option.value ? 'selected' : ''}`}
                  onClick={() => {
                    handleSelect(option.value);
                    setUseCustomGoal(false);
                    setCustomGoal('');
                  }}
                >
                  <div className="option-icon">{option.icon}</div>
                  <div className="option-text">
                    <div className="option-label">{option.label}</div>
                  </div>
                </button>
              ))}
            </div>

            <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: '20px' }}>
              <button
                className={`option-button ${useCustomGoal ? 'selected' : ''}`}
                onClick={() => {
                  setUseCustomGoal(!useCustomGoal);
                  if (!useCustomGoal) {
                    setForm({ ...form, goal: '' });
                  }
                }}
                style={{ width: '100%', marginBottom: '12px' }}
              >
                <div className="option-icon">✏️</div>
                <div className="option-text">
                  <div className="option-label">Custom Goal</div>
                </div>
              </button>

              {useCustomGoal && (
                <input
                  type="text"
                  placeholder="Enter your custom wellness goal..."
                  value={customGoal}
                  onChange={(e) => setCustomGoal(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #10b981',
                    borderRadius: '8px',
                    fontSize: '16px',
                    boxShadow: '0 0 0 3px rgba(16, 185, 129, 0.1)',
                  }}
                />
              )}
            </div>
          </div>
        )}

        <div className="onboarding-actions">
          {currentStep > 0 && (
            <button
              className="btn-back"
              onClick={() => setCurrentStep(currentStep - 1)}
              disabled={saving}
            >
              Back
            </button>
          )}
          <button
            className="btn-next"
            onClick={handleNext}
            disabled={!isStepComplete || saving}
          >
            {saving ? 'Saving...' : isLastStep ? 'Complete' : 'Next'}
          </button>
        </div>

        <div className="step-indicator">
          Step <strong>{currentStep + 1}</strong> of <strong>{steps.length}</strong>
        </div>
      </div>
    </div>
  );
}

function getAgeIcon(range) {
  if (range.includes('18-25')) return '🎓';
  if (range.includes('26-35')) return '💼';
  if (range.includes('36-45')) return '🏃';
  if (range.includes('46-55')) return '🧘';
  if (range.includes('56-65')) return '🌳';
  return '👤';
}

function getWeightIcon(range) {
  if (range.includes('100-120')) return '🪶';
  if (range.includes('120-150')) return '⚖️';
  if (range.includes('150-180')) return '💪';
  if (range.includes('180-210')) return '🏋️';
  if (range.includes('210')) return '🦾';
  return '⚖️';
}

function getActivityIcon(level) {
  if (level === 'sedentary') return '🛋️';
  if (level === 'lightly_active') return '🚶';
  if (level === 'moderately_active') return '🏃';
  if (level === 'very_active') return '🏋️';
  if (level === 'extremely_active') return '⚡';
  return '🏃';
}

function getGoalIcon(goal) {
  if (goal.includes('lose') || goal.includes('weight')) return '📉';
  if (goal.includes('gain') || goal.includes('muscle')) return '💪';
  if (goal.includes('maintain') || goal.includes('balance')) return '⚖️';
  if (goal.includes('energy') || goal.includes('performance')) return '⚡';
  if (goal.includes('health') || goal.includes('wellness')) return '🌿';
  return '🎯';
}
