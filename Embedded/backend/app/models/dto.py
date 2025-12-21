from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator

class DatasetItem(BaseModel):
  id: str
  name: str
  label: str = Field(pattern=r"^(ok|missing)$")
  sizeBytes: int
  createdAt: datetime
  path: str

class TrainRequest(BaseModel):
  boardName: str = Field(default="PCB", min_length=1, max_length=100)
  epochs: int = Field(default=20) 
  testSplit: float = Field(default=0.2)

class TrainingJob(BaseModel):
  jobId: str
  status: str
  progress: float = 0.0
  message: Optional[str] = None
  boardName: Optional[str] = None
  metrics: Optional[Dict[str, Any]] = None

  @validator("progress")
  def clamp_progress(cls, value: float) -> float:
    return max(0.0, min(1.0, value))

class BoundingBox(BaseModel):
  x: float
  y: float
  width: float
  height: float

class MissingArea(BaseModel):
  id: str
  description: str
  confidence: float
  bbox: Optional[BoundingBox] = None

class InferenceResponse(BaseModel):
  isDefective: bool
  confidence: float
  timestamp: datetime
  missingAreas: List[MissingArea] = Field(default_factory=list)
  notes: Optional[str]
  boardName: str = "Unknown" 

class ComponentTemplate(BaseModel):
    id: int
    label: str 
    box: List[float] 

class BoardProfile(BaseModel):
    boardName: str
    created_at: datetime
    reference_image_path: str
    components: List[ComponentTemplate]