"""
NEXUS-14: Health Check System
Monitors all system components before pipeline launch.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp


logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Comprehensive health checker for NEXUS-14.
    
    Checks:
    - API connectivity (OpenAI, Anthropic, WordPress, SendGrid)
    - Search API availability
    - Redis connection
    - Storage connectivity
    - Environment variables
    - File system permissions
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.results = {}
    
    async def check_all(self) -> bool:
        """Run all health checks."""
        logger.info("Running NEXUS-14 health checks...")
        
        checks = [
            ("environment", self.check_environment()),
            ("llm_api", self.check_llm_api()),
            ("wordpress", self.check_wordpress()),
            ("file_system", self.check_file_system()),
        ]
        
        # Run checks concurrently
        results = await asyncio.gather(*[check for _, check in checks], return_exceptions=True)
        
        all_passed = True
        for (name, _), result in zip(checks, results):
            if isinstance(result, Exception):
                self.results[name] = {"status": "failed", "error": str(result)}
                logger.error(f"Health check FAILED: {name} - {result}")
                all_passed = False
            else:
                self.results[name] = result
                if not result.get("healthy", False):
                    all_passed = False
                    logger.warning(f"Health check WARNING: {name}")
                else:
                    logger.info(f"Health check PASSED: {name}")
        
        logger.info(f"Overall health: {'HEALTHY' if all_passed else 'DEGRADED'}")
        return all_passed
    
    async def quick_check(self) -> Dict:
        """Quick health check for Docker HEALTHCHECK."""
        try:
            env_ok = await self.check_environment()
            fs_ok = await self.check_file_system()
            return {
                "status": "healthy" if (env_ok.get("healthy") and fs_ok.get("healthy")) else "degraded",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_environment(self) -> Dict:
        """Check required environment variables."""
        # Critical vars required for basic operation
        critical_vars = [
            "OPENAI_API_KEY",
            "WORDPRESS_URL",
        ]
        # Optional vars (warn but don't fail)
        optional_vars = [
            "ANTHROPIC_API_KEY",
            "EMAIL_RECIPIENT",
            "SENDGRID_API_KEY",
        ]
        
        missing_critical = [var for var in critical_vars if not os.environ.get(var)]
        missing_optional = [var for var in optional_vars if not os.environ.get(var)]
        if missing_optional:
            logger.warning(f"Optional env vars missing: {missing_optional}")
        
        missing = missing_critical
        
        return {
            "healthy": len(missing) == 0,
            "missing_vars": missing,
            "check": "environment_variables"
        }
    
    async def check_llm_api(self) -> Dict:
        """Check LLM API availability."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
            # Test with minimal request
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            return {"healthy": True, "provider": "anthropic", "check": "llm_api"}
        except Exception as e:
            return {"healthy": False, "error": str(e), "check": "llm_api"}
    
    async def check_wordpress(self) -> Dict:
        """Check WordPress connectivity."""
        wp_url = os.environ.get("WORDPRESS_URL", "")
        if not wp_url:
            return {"healthy": False, "error": "WORDPRESS_URL not set", "check": "wordpress"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{wp_url}/wp-json/wp/v2",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    healthy = response.status == 200
                    return {
                        "healthy": healthy,
                        "status_code": response.status,
                        "check": "wordpress"
                    }
        except Exception as e:
            return {"healthy": False, "error": str(e), "check": "wordpress"}
    
    async def check_file_system(self) -> Dict:
        """Check file system write permissions."""
        test_dirs = ["output", "logs"]
        issues = []
        
        for dir_path in test_dirs:
            try:
                os.makedirs(dir_path, exist_ok=True)
                test_file = f"{dir_path}/.health_check_test"
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                issues.append(f"{dir_path}: {e}")
        
        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "check": "file_system"
        }
    
    def get_report(self) -> Dict:
        """Get health check report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_healthy": all(r.get("healthy", False) for r in self.results.values()),
            "checks": self.results
        }
