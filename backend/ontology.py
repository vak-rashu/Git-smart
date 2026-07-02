import logging
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger(__name__)

# In Cognee, custom entities should ideally subclass `DataPoint`.
# We use a fallback to BaseModel so the app doesn't crash if imports fail.
try:
    from cognee.infrastructure.engine import DataPoint
    BaseClass = DataPoint
except ImportError:
    BaseClass = BaseModel
    logger.warning("Could not import cognee DataPoint. Using Pydantic BaseModel instead.")

class AIAgent(BaseClass):
    """Represents an autonomous AI agent or LLM wrapper."""
    name: str = Field(..., description="Name of the AI Agent (e.g., mausam-agent, openclaw)")
    purpose: Optional[str] = Field(None, description="What the agent is designed to do")

class SoftwareFramework(BaseClass):
    """Represents a software framework or library."""
    name: str = Field(..., description="Name of the framework (e.g., FastAPI, React)")
    language: Optional[str] = Field(None, description="Programming language used")

class Infrastructure(BaseClass):
    """Represents databases, message queues, or other infrastructure."""
    name: str = Field(..., description="Name of the infrastructure component")
    type: Optional[str] = Field(None, description="Type (e.g., Database, Queue, Cache)")

class CodeArtifact(BaseClass):
    """Represents code files, functions, or classes within a repository."""
    name: str = Field(..., description="Name of the artifact or filepath")
    artifact_type: Optional[str] = Field(None, description="Type of artifact (e.g., file, class, method)")
    
class SoftwareComponent(BaseClass):
    """Represents microservices, APIs, or internal system modules."""
    name: str = Field(..., description="Name of the component")
    description: Optional[str] = Field(None, description="Description of the component")

class Developer(BaseClass):
    """Represents a human developer, contributor, or author."""
    name: str = Field(..., description="Name or username of the developer")

def init_ontology():
    """
    Initializes and registers the custom ontology.
    Simply importing this module and these classes makes them available in the Python runtime,
    allowing Cognee's Pydantic/DataPoint inspection to map them.
    """
    logger.info("Custom Software Engineering Ontology loaded.")
