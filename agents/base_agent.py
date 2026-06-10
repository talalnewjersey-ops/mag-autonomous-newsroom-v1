"""
NEXUS-14: Base Agent Class
All 14 agents inherit from this base class.
"""

import logging
import json
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from services.storage_service import StorageService
from services.llm_service import LLMService


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all NEXUS-14 agents.
    Provides common functionality: logging, error handling,
    output saving, LLM calls, retry logic.
    """
    
    AGENT_ID = "base"
    AGENT_NAME = "Base Agent"
    VERSION = "1.0.0"
    
    def __init__(self, config: Dict, llm_service: LLMService, storage_service: StorageService):
        self.config = config
        self.llm = llm_service
        self.storage = storage_service
        self.logger = logging.getLogger(f"NEXUS14.{self.AGENT_NAME}")
        self.start_time = None
        self.errors = []
        self.warnings = []
        
        # Output directory
        self.output_dir = Path(config.get("output_dir", "output")) / self.AGENT_ID
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    @abstractmethod
    async def run(self, context: Dict = None) -> Dict:
        """Main agent execution. Must be implemented by each agent."""
        pass
    
    def log_start(self):
        """Log agent start."""
        self.start_time = datetime.utcnow()
        self.logger.info(f"{'='*50}")
        self.logger.info(f"  {self.AGENT_NAME} (v{self.VERSION}) STARTED")
        self.logger.info(f"  Time: {self.start_time.isoformat()}")
        self.logger.info(f"{'='*50}")
    
    def log_complete(self, stats: Dict = None):
        """Log agent completion."""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds() if self.start_time else 0
        
        self.logger.info(f"{'='*50}")
        self.logger.info(f"  {self.AGENT_NAME} COMPLETED")
        self.logger.info(f"  Duration: {duration:.2f}s")
        if stats:
            for key, value in stats.items():
                self.logger.info(f"  {key}: {value}")
        if self.errors:
            self.logger.warning(f"  Errors encountered: {len(self.errors)}")
        self.logger.info(f"{'='*50}")
    
    def log_error(self, error: Exception):
        """Log agent error."""
        self.errors.append(str(error))
        self.logger.error(f"{self.AGENT_NAME} ERROR: {error}", exc_info=True)
    
    def log_warning(self, message: str):
        """Log agent warning."""
        self.warnings.append(message)
        self.logger.warning(f"{self.AGENT_NAME} WARNING: {message}")
    
    async def save_output(self, filename: str, data: Any) -> Path:
        """Save output data to file."""
        output_path = self.output_dir / filename
        
        if filename.endswith('.json'):
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        elif filename.endswith('.md') or filename.endswith('.html'):
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(data)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(str(data))
        
        self.logger.info(f"Output saved: {output_path}")
        
        # Also save to storage service (S3/cloud)
        try:
            await self.storage.save(str(output_path), data)
        except Exception as e:
            self.log_warning(f"Failed to save to cloud storage: {e}")
        
        return output_path
    
    async def call_llm(self, prompt: str, system: str = None, 
                       model: str = None, max_tokens: int = 4096) -> str:
        """Call the LLM service with retry logic."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = await self.llm.complete(
                    prompt=prompt,
                    system=system,
                    model=model,
                    max_tokens=max_tokens
                )
                return response
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    self.log_warning(f"LLM call failed (attempt {attempt+1}): {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
    
    def get_status(self) -> Dict:
        """Get current agent status."""
        return {
            "agent_id": self.AGENT_ID,
            "agent_name": self.AGENT_NAME,
            "version": self.VERSION,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "status": "running" if self.start_time else "idle"
        }
    
    async def validate_output(self, output: Dict) -> bool:
        """Validate agent output. Override in subclass for custom validation."""
        return bool(output)
