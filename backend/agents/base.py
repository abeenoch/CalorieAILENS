import json
from typing import Optional, Any
from abc import ABC, abstractmethod

from google import genai
from google.genai import types
from groq import AsyncGroq

from config import get_settings

settings = get_settings()


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self):
        """Initialize the agent with both Gemini and Groq clients."""
        # Gemini for vision only
        self.gemini_client = genai.Client(api_key=settings.google_api_key)
        self.gemini_model = settings.gemini_model
        
        # Groq for text generation (AsyncGroq for async support)
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
        self.groq_model = settings.groq_model
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name for logging and tracing."""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for the agent."""
        pass
    
    async def generate_text(
        self,
        prompt: str,
        image_data: Optional[bytes] = None,
        image_mime_type: str = "image/jpeg"
    ) -> str:
        """
        Generate text response using appropriate AI model.
        
        Args:
            prompt: The text prompt
            image_data: Optional image bytes for vision tasks (uses Gemini)
            image_mime_type: MIME type of the image
            
        Returns:
            Generated text response
        """
        # Use Gemini for vision tasks
        if image_data:
            return await self._generate_with_gemini_vision(prompt, image_data, image_mime_type)
        
        # Use Groq for text-only tasks (much faster and unlimited free tier)
        return await self._generate_with_groq(prompt)
    
    async def _generate_with_gemini_vision(
        self,
        prompt: str,
        image_data: bytes,
        image_mime_type: str
    ) -> str:
        """Generate response using Gemini for vision tasks."""
        contents = []
        
        # Add system prompt
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=f"System: {self.system_prompt}")]
        ))
        
        # Build content with image and text
        parts = [
            types.Part.from_bytes(
                data=image_data,
                mime_type=image_mime_type
            ),
            types.Part(text=prompt)
        ]
        
        contents.append(types.Content(
            role="user",
            parts=parts
        ))
        
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2048,
                )
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error in {self.name}: {str(e)}")
    
    async def _generate_with_groq(self, prompt: str) -> str:
        """Generate response using Groq for text-only tasks."""
        try:
            # Combine system prompt with user prompt
            full_prompt = f"System: {self.system_prompt}\n\nUser: {prompt}"
            
            message = await self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            return message.choices[0].message.content
        except Exception as e:
            raise Exception(f"Groq API error in {self.name}: {str(e)}")
    
    def parse_json_response(self, response: str) -> dict:
        """
        Parse JSON from LLM response, handling markdown code blocks and common malformations.
        
        Args:
            response: Raw text response from LLM
            
        Returns:
            Parsed JSON dictionary
        """
        # Clean up response - remove markdown code blocks if present
        cleaned = response.strip()
        
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        # Try direct parsing first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # Try to find and extract JSON object
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}") + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_part = cleaned[start_idx:end_idx]
            
            # Try parsing the extracted JSON
            try:
                return json.loads(json_part)
            except json.JSONDecodeError:
                pass
            
            # Fix common JSON issues
            # Remove trailing commas before closing braces/brackets
            json_part = json_part.replace(",}", "}")
            json_part = json_part.replace(",]", "]")
            
            # Try again after fixing trailing commas
            try:
                return json.loads(json_part)
            except json.JSONDecodeError:
                pass
        
        # If all parsing attempts fail, raise error with context
        raise Exception(f"Failed to parse JSON from {self.name}: Invalid JSON format\nResponse: {response[:500]}")
    
    @abstractmethod
    async def process(self, *args, **kwargs) -> dict:
        """Process input and return structured output."""
        pass
