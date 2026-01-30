import { useContext } from 'react';
import { AuthContext } from '../App';
import { 
  Camera, 
  TrendingUp, 
  Heart, 
  Zap,
  ChevronRight,
  Sparkles,
  BarChart3,
  Brain
} from 'lucide-react';

export function LandingPage({ onSignUpClick, onLoginClick }) {
  return (
    <div className="landing-page">
      <HeroSection onSignUpClick={onSignUpClick} onLoginClick={onLoginClick} />
      <FeaturesSection />
      <HowItWorks />
    </div>
  );
}

function HeroSection({ onSignUpClick, onLoginClick }) {
  return (
    <section className="hero-section" aria-label="Hero section">
      <div className="hero-badge">
        <Sparkles size={16} />
        <span>AI-Powered Nutrition</span>
      </div>
      <div className="hero-content">
        <h1 className="hero-headline">
          Track Your Wellness, <span className="highlight">Not Just Calories</span>
        </h1>
        <p className="hero-subheading">
          Calorie AI Tracker uses multi-agent AI to analyze your meals, understand your nutrition, and provide personalized wellness insights—without judgment.
        </p>
        <div className="hero-ctas" role="group" aria-label="Call to action buttons">
          <button 
            className="btn btn-primary btn-lg" 
            onClick={onSignUpClick}
            aria-label="Get started with Calorie Tracker"
          >
            <Zap size={18} />
            Get Started Free
          </button>
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  const features = [
    {
      icon: Camera,
      title: 'Photo Analysis',
      description: 'Snap a photo of your meal. Our AI identifies foods and calculates nutrition instantly.',
    },
    {
      icon: BarChart3,
      title: 'Smart Insights',
      description: 'Get personalized recommendations based on your goals and eating patterns.',
    },
    {
      icon: Heart,
      title: 'Wellness First',
      description: 'Supportive, non-judgmental approach focused on your overall wellbeing.',
    },
  ];

  return (
    <section className="features-section" aria-label="Key features">
      <div className="features-container">
        <h2 className="section-title">Why Choose Calorie AI Tracker?</h2>
        <div className="features-grid" role="list">
          {features.map((feature, index) => (
            <FeatureCard key={index} feature={feature} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FeatureCard({ feature: { icon: Icon, title, description } }) {
  return (
    <div className="feature-card card" role="listitem">
      <div className="feature-icon">
        <Icon size={40} strokeWidth={1.5} />
      </div>
      <h3 className="feature-title">{title}</h3>
      <p className="feature-description">{description}</p>
    </div>
  );
}

function HowItWorks() {
  const steps = [
    {
      number: 1,
      title: 'Log Meals',
      description: 'Take a photo of your meal or scan a barcode',
      icon: Camera,
    },
    {
      number: 2,
      title: 'AI Analysis',
      description: 'Our AI identifies foods and calculates calories',
      icon: Brain,
    },
    {
      number: 3,
      title: 'Track Progress',
      description: 'Monitor your wellness journey with visual insights',
      icon: TrendingUp,
    },
  ];

  return (
    <section className="how-it-works" aria-label="How it works">
      <div className="how-it-works-container">
        <h2 className="section-title">How It Works</h2>
        <div className="steps-grid" role="list">
          {steps.map((step, index) => (
            <div key={index} className="step" role="listitem">
              <div className="step-number" aria-label={`Step ${step.number}`}>{step.number}</div>
              <div className="step-icon">
                <step.icon size={48} strokeWidth={1.5} />
              </div>
              <h3 className="step-title">{step.title}</h3>
              <p className="step-description">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
