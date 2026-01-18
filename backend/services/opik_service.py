import os
from typing import Optional, Any
from functools import wraps

import opik
from opik import track, opik_context

from config import get_settings

settings = get_settings()


def init_opik():
    """Initialize Opik with configuration from environment."""
    # Set environment variables for Opik
    if settings.opik_api_key:
        os.environ["OPIK_API_KEY"] = settings.opik_api_key
    if settings.opik_workspace:
        os.environ["OPIK_WORKSPACE"] = settings.opik_workspace
    if settings.opik_url_override:
        os.environ["OPIK_URL_OVERRIDE"] = settings.opik_url_override
    
    # Configure Opik
    try:
        opik.configure(
            api_key=settings.opik_api_key if settings.opik_api_key else None,
            workspace=settings.opik_workspace if settings.opik_workspace else None,
            use_local=not settings.opik_api_key  # Use local if no API key
        )
        print(f"Opik initialized for project: {settings.opik_project_name}")
    except Exception as e:
        print(f"Opik initialization warning: {e}")


def get_opik_client():
    """Get Opik client instance."""
    return opik.Opik(
        project_name=settings.opik_project_name
    )


class OpikMetrics:
    """Helper class for logging custom metrics to Opik."""
    
    @staticmethod
    def log_confidence(confidence: str, trace_id: Optional[str] = None):
        """Log confidence score metric."""
        try:
            opik_context.update_current_span(
                metadata={"confidence_score": confidence}
            )
        except Exception:
            pass  # Silently fail if not in a trace context
    
    @staticmethod
    def log_image_ambiguity(ambiguity: str, trace_id: Optional[str] = None):
        """Log image ambiguity level."""
        try:
            opik_context.update_current_span(
                metadata={"image_ambiguity": ambiguity}
            )
        except Exception:
            pass
    
    @staticmethod
    def log_user_correction(correction_type: str, meal_id: int):
        """Log user correction for model improvement tracking."""
        try:
            opik_context.update_current_span(
                metadata={
                    "user_correction": correction_type,
                    "meal_id": meal_id
                }
            )
        except Exception:
            pass
    
    @staticmethod
    def log_agent_output(agent_name: str, output: dict):
        """Log agent output for debugging."""
        try:
            opik_context.update_current_span(
                metadata={f"{agent_name}_output": output}
            )
        except Exception:
            pass


def track_agent(agent_name: str):
    """
    Decorator to track agent execution in Opik.
    Wraps the @track decorator with agent-specific metadata.
    """
    def decorator(func):
        @track(name=agent_name, project_name=settings.opik_project_name)
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            return result
        return wrapper
    return decorator


#def flush_traces():
#    """Flush all pending traces to Opik."""
#    try:
#        flush_tracker()
#    except Exception as e:
#        print(f"Warning: Could not flush Opik traces: {e}")


# Pre-configured decorators for each agent
def track_vision_interpreter(func):
    """Track Vision Interpreter agent."""
    return track(name="vision_interpreter", project_name=settings.opik_project_name)(func)


def track_nutrition_reasoner(func):
    """Track Nutrition Reasoner agent."""
    return track(name="nutrition_reasoner", project_name=settings.opik_project_name)(func)


def track_personalization_agent(func):
    """Track Personalization Agent."""
    return track(name="personalization_agent", project_name=settings.opik_project_name)(func)


def track_wellness_coach(func):
    """Track Wellness Coach agent."""
    return track(name="wellness_coach", project_name=settings.opik_project_name)(func)


def track_orchestrator(func):
    """Track the main orchestrator that chains all agents."""
    return track(name="meal_analysis_orchestrator", project_name=settings.opik_project_name)(func)
