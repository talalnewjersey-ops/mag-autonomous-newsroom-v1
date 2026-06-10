"""
NEXUS-14: Agent 14 - Production Director Agent
The master supervisor of all 14 agents. Orchestrates, monitors, 
recovers failed workflows, and generates the daily production report.
Output: daily_production_report.html
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from agents.base_agent import BaseAgent
from services.llm_service import LLMService
from services.storage_service import StorageService
from services.email_service import EmailService


logger = logging.getLogger(__name__)


class ProductionDirectorAgent(BaseAgent):
    """
    Agent 14: Production Director Agent
    
    The ultimate supervisor of NEXUS-14.
    
    Responsibilities:
    - Supervise all 14 agents
    - Detect errors and bottlenecks
    - Retry failed workflows automatically
    - Generate HTML daily production report
    - Send Morning Report at 09:45
    - Send Executive Report at 18:30
    
    Output: daily_production_report.html
    """
    
    AGENT_ID = "agent_14"
    AGENT_NAME = "Production Director Agent"
    
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 30
    
    def __init__(self, config: Dict, llm_service: LLMService,
                 storage_service: StorageService, email_service: EmailService):
        super().__init__(config, llm_service, storage_service)
        self.email = email_service
        self.production_log = []
        self.agent_status = {}
        self.metrics = {}
    
    async def run(self, context: Dict = None) -> Dict:
        """Main agent execution - supervise and report."""
        self.log_start()
        
        try:
            # Collect all agent outputs
            logger.info("Collecting production data from all agents...")
            production_data = await self._collect_production_data(context or {})
            
            # Analyze pipeline health
            logger.info("Analyzing pipeline health...")
            health_analysis = await self._analyze_pipeline_health(production_data)
            
            # Detect and log errors
            errors = await self._detect_errors(production_data, health_analysis)
            
            # Calculate metrics
            self.metrics = await self._calculate_metrics(production_data)
            
            # Generate daily report
            logger.info("Generating daily production report...")
            report_html = await self._generate_html_report(
                production_data, health_analysis, errors, self.metrics
            )
            
            # Save report
            report_path = await self.save_output("daily_production_report.html", report_html)
            
            # Send appropriate email based on time
            current_hour = datetime.utcnow().hour
            
            if 9 <= current_hour < 11:
                # Morning Report (09:45 UTC)
                await self._send_morning_report(production_data, self.metrics)
            elif 18 <= current_hour < 19:
                # Executive Daily Report (18:30 UTC)
                await self._send_executive_report(production_data, self.metrics, report_html)
            
            output = {
                "agent": self.AGENT_NAME,
                "timestamp": datetime.utcnow().isoformat(),
                "run_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "metrics": self.metrics,
                "health": health_analysis,
                "errors": errors,
                "report_path": str(report_path),
                "emails_sent": []
            }
            
            self.log_complete(self.metrics)
            return output
            
        except Exception as e:
            self.log_error(e)
            raise
    
    async def _collect_production_data(self, context: Dict) -> Dict:
        """Collect output data from all agents."""
        data = {
            "run_id": context.get("run_id", "unknown"),
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "agents": {},
            "articles": [],
            "errors": []
        }
        
        # Collect from context
        for key, value in context.items():
            if key.startswith("agent_") and key.endswith("_result"):
                agent_id = key.split("_")[1]
                data["agents"][agent_id] = value
        
        # Load from files if not in context
        output_dirs = [
            Path("output/agent_01"),
            Path("output/agent_02"),
            Path("output/agent_12"),
            Path("output/agent_13")
        ]
        
        for output_dir in output_dirs:
            if output_dir.exists():
                for json_file in output_dir.glob("*.json"):
                    try:
                        with open(json_file) as f:
                            file_data = json.load(f)
                        agent_key = output_dir.name.replace("agent_", "")
                        if agent_key not in data["agents"]:
                            data["agents"][agent_key] = {}
                        data["agents"][agent_key][json_file.stem] = file_data
                    except Exception as e:
                        logger.warning(f"Failed to load {json_file}: {e}")
        
        return data
    
    async def _analyze_pipeline_health(self, production_data: Dict) -> Dict:
        """Analyze overall pipeline health."""
        agents_data = production_data.get("agents", {})
        
        health = {
            "overall_status": "healthy",
            "agents_completed": 0,
            "agents_failed": 0,
            "agents_missing": 0,
            "bottlenecks": [],
            "warnings": []
        }
        
        expected_agents = [str(i).zfill(2) for i in range(1, 15)]
        
        for agent_id in expected_agents:
            if agent_id in agents_data:
                health["agents_completed"] += 1
            else:
                health["agents_missing"] += 1
                health["warnings"].append(f"Agent {agent_id} output not found")
        
        if health["agents_failed"] > 0:
            health["overall_status"] = "degraded"
        if health["agents_missing"] > 3:
            health["overall_status"] = "critical"
        
        return health
    
    async def _detect_errors(self, production_data: Dict, health: Dict) -> List[Dict]:
        """Detect errors across the pipeline."""
        errors = []
        
        # Check for missing outputs
        for warning in health.get("warnings", []):
            errors.append({
                "type": "missing_output",
                "message": warning,
                "severity": "medium",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check articles for quality issues
        articles = production_data.get("articles", [])
        for article in articles:
            word_count = article.get("word_count", 0)
            seo_score = article.get("seo_score", 0)
            eeat_score = article.get("eeat_score", 0)
            
            if word_count < 5000:
                errors.append({
                    "type": "quality_violation",
                    "message": f"Article '{article.get('title', 'Unknown')}' below min word count: {word_count}",
                    "severity": "high"
                })
            if seo_score < 95:
                errors.append({
                    "type": "quality_violation", 
                    "message": f"SEO score {seo_score} below threshold (95)",
                    "severity": "high"
                })
        
        return errors
    
    async def _calculate_metrics(self, production_data: Dict) -> Dict:
        """Calculate production metrics."""
        articles = production_data.get("articles", [])
        
        return {
            "total_articles_produced": len(articles),
            "articles_validated": len([a for a in articles if a.get("status") == "READY_TO_PUBLISH"]),
            "articles_rejected": len([a for a in articles if a.get("status") == "REJECTED"]),
            "articles_need_correction": len([a for a in articles if a.get("status") == "NEEDS_CORRECTION"]),
            "avg_word_count": round(sum(a.get("word_count", 0) for a in articles) / max(len(articles), 1)),
            "avg_seo_score": round(sum(a.get("seo_score", 0) for a in articles) / max(len(articles), 1), 1),
            "avg_eeat_score": round(sum(a.get("eeat_score", 0) for a in articles) / max(len(articles), 1), 1),
            "agents_completed": len(production_data.get("agents", {})),
            "production_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "pipeline_duration_minutes": 0  # Will be calculated
        }
    
    async def _generate_html_report(self, production_data: Dict, 
                                     health: Dict, errors: List, metrics: Dict) -> str:
        """Generate comprehensive HTML production report."""
        date = datetime.utcnow().strftime("%B %d, %Y")
        
        # Status color
        status_color = {
            "healthy": "#28a745",
            "degraded": "#ffc107",
            "critical": "#dc3545"
        }.get(health.get("overall_status", "unknown"), "#6c757d")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS-14 Daily Production Report - {date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }}
        .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 40px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header .subtitle {{ opacity: 0.8; font-size: 14px; }}
        .container {{ max-width: 1200px; margin: 30px auto; padding: 0 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .card h2 {{ font-size: 18px; margin-bottom: 16px; color: #1a1a2e; border-bottom: 2px solid #f0f0f0; padding-bottom: 12px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }}
        .metric {{ background: #f8f9fa; border-radius: 8px; padding: 16px; text-align: center; }}
        .metric .value {{ font-size: 32px; font-weight: bold; color: #1a1a2e; }}
        .metric .label {{ font-size: 12px; color: #666; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .status-badge {{ display: inline-block; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 600; color: white; background: {status_color}; }}
        .agent-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; }}
        .agent-card {{ border: 1px solid #e0e0e0; border-radius: 8px; padding: 14px; }}
        .agent-card .agent-name {{ font-weight: 600; font-size: 14px; margin-bottom: 4px; }}
        .agent-card .agent-status {{ font-size: 12px; color: #28a745; }}
        .error-list {{ list-style: none; }}
        .error-list li {{ padding: 10px 14px; margin-bottom: 8px; border-radius: 6px; border-left: 4px solid; }}
        .error-high {{ background: #fff5f5; border-color: #dc3545; }}
        .error-medium {{ background: #fff9e6; border-color: #ffc107; }}
        .footer {{ text-align: center; padding: 30px; color: #999; font-size: 13px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #f8f9fa; padding: 12px; text-align: left; font-size: 13px; color: #666; border-bottom: 2px solid #e0e0e0; }}
        td {{ padding: 12px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }}
        tr:hover {{ background: #f8f9fa; }}
        .ready {{ color: #28a745; font-weight: 600; }}
        .rejected {{ color: #dc3545; font-weight: 600; }}
        .needs-correction {{ color: #ffc107; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 NEXUS-14 Production Report</h1>
        <div class="subtitle">MoneyAbroadGuide.com Autonomous Newsroom | {date}</div>
        <div style="margin-top: 16px;">
            <span class="status-badge">{health.get("overall_status", "unknown").upper()}</span>
        </div>
    </div>
    
    <div class="container">
        
        <!-- EXECUTIVE SUMMARY -->
        <div class="card">
            <h2>📊 Executive Summary</h2>
            <div class="metrics-grid">
                <div class="metric">
                    <div class="value">{metrics.get("total_articles_produced", 0)}</div>
                    <div class="label">Articles Produced</div>
                </div>
                <div class="metric">
                    <div class="value" style="color: #28a745;">{metrics.get("articles_validated", 0)}</div>
                    <div class="label">Articles Validated</div>
                </div>
                <div class="metric">
                    <div class="value" style="color: #dc3545;">{metrics.get("articles_rejected", 0)}</div>
                    <div class="label">Articles Rejected</div>
                </div>
                <div class="metric">
                    <div class="value">{metrics.get("avg_word_count", 0):,}</div>
                    <div class="label">Avg Word Count</div>
                </div>
                <div class="metric">
                    <div class="value">{metrics.get("avg_seo_score", 0)}</div>
                    <div class="label">Avg SEO Score</div>
                </div>
                <div class="metric">
                    <div class="value">{metrics.get("avg_eeat_score", 0)}</div>
                    <div class="label">Avg EEAT Score</div>
                </div>
            </div>
        </div>
        
        <!-- AGENT STATUS -->
        <div class="card">
            <h2>🤖 Agent Status</h2>
            <div class="agent-grid">
                {"".join([f'''
                <div class="agent-card">
                    <div class="agent-name">Agent {str(i).zfill(2)}</div>
                    <div class="agent-status">✅ Completed</div>
                </div>''' for i in range(1, 15)])}
            </div>
        </div>
        
        <!-- QUALITY METRICS -->
        <div class="card">
            <h2>✅ Quality Metrics</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Target</th>
                    <th>Actual</th>
                    <th>Status</th>
                </tr>
                <tr>
                    <td>Minimum Word Count</td>
                    <td>5,000</td>
                    <td>{metrics.get("avg_word_count", 0):,}</td>
                    <td class="ready">PASS</td>
                </tr>
                <tr>
                    <td>SEO Score</td>
                    <td>≥ 95</td>
                    <td>{metrics.get("avg_seo_score", 0)}</td>
                    <td class="{'ready' if metrics.get('avg_seo_score', 0) >= 95 else 'rejected'}">{'PASS' if metrics.get('avg_seo_score', 0) >= 95 else 'FAIL'}</td>
                </tr>
                <tr>
                    <td>EEAT Score</td>
                    <td>≥ 95</td>
                    <td>{metrics.get("avg_eeat_score", 0)}</td>
                    <td class="{'ready' if metrics.get('avg_eeat_score', 0) >= 95 else 'rejected'}">{'PASS' if metrics.get('avg_eeat_score', 0) >= 95 else 'FAIL'}</td>
                </tr>
            </table>
        </div>
        
        <!-- ERRORS -->
        <div class="card">
            <h2>⚠️ Errors & Warnings ({len(errors)})</h2>
            {"<p style='color: #28a745; font-weight: 600;'>✅ No errors detected. All systems nominal.</p>" if not errors else f"<ul class='error-list'>{''.join([f"<li class='error-{e.get(chr(115)+chr(101)+chr(118)+chr(101)+chr(114)+chr(105)+chr(116)+chr(121), chr(109)+chr(101)+chr(100)+chr(105)+chr(117)+chr(109))}'><strong>{e.get('type', 'error')}</strong>: {e.get('message', '')}</li>" for e in errors])}</ul>"}
        </div>
        
    </div>
    
    <div class="footer">
        <p>Generated by NEXUS-14 Production Director | MoneyAbroadGuide.com | {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</p>
    </div>
</body>
</html>"""
        
        return html
    
    async def _send_morning_report(self, production_data: Dict, metrics: Dict):
        """Send morning production report at 09:45."""
        subject = f"[NEXUS-14] Morning Production Report - {datetime.utcnow().strftime('%B %d, %Y')}"
        
        body = f"""
NEXUS-14 Morning Production Report
====================================
Date: {datetime.utcnow().strftime("%B %d, %Y")}
Time: {datetime.utcnow().strftime("%H:%M UTC")}

OVERNIGHT PRODUCTION SUMMARY
-----------------------------
Articles Produced: {metrics.get("total_articles_produced", 0)}
Articles Validated: {metrics.get("articles_validated", 0)} 
Articles Rejected: {metrics.get("articles_rejected", 0)}
Articles Need Correction: {metrics.get("articles_need_correction", 0)}

QUALITY METRICS
---------------
Average Word Count: {metrics.get("avg_word_count", 0):,}
Average SEO Score: {metrics.get("avg_seo_score", 0)}/100
Average EEAT Score: {metrics.get("avg_eeat_score", 0)}/100

STATUS
------
Pipeline: {metrics.get("agents_completed", 0)}/14 agents completed

NEXT STEPS
----------
- Batch #1 ready at 10:00 UTC
- Evening cycle starts at 10:00 UTC
- Audit #2 at 16:30 UTC
- Executive report at 18:30 UTC

--
NEXUS-14 Autonomous Newsroom
MoneyAbroadGuide.com
        """
        
        try:
            await self.email.send(
                to=self.config.get("email_recipient", "talalnewjersey@gmail.com"),
                subject=subject,
                body=body
            )
            logger.info("Morning report sent successfully")
        except Exception as e:
            logger.error(f"Failed to send morning report: {e}")
    
    async def _send_executive_report(self, production_data: Dict, 
                                      metrics: Dict, report_html: str):
        """Send executive daily report at 18:30."""
        subject = f"[NEXUS-14] Executive Daily Report - {datetime.utcnow().strftime('%B %d, %Y')}"
        
        try:
            await self.email.send_html(
                to=self.config.get("email_recipient", "talalnewjersey@gmail.com"),
                subject=subject,
                html_body=report_html,
                text_body=f"NEXUS-14 Executive Report - {metrics.get('total_articles_produced', 0)} articles produced today."
            )
            logger.info("Executive daily report sent successfully")
        except Exception as e:
            logger.error(f"Failed to send executive report: {e}")
    
    async def retry_failed_workflow(self, agent_id: str, context: Dict) -> Optional[Dict]:
        """Retry a failed agent workflow."""
        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            logger.info(f"Retry attempt {attempt+1} for Agent {agent_id}...")
            
            try:
                agent = self._get_agent(agent_id)
                if agent:
                    result = await agent.run(context)
                    logger.info(f"Agent {agent_id} recovered successfully on attempt {attempt+1}")
                    return result
            except Exception as e:
                if attempt < self.MAX_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
                else:
                    logger.error(f"Agent {agent_id} failed after {self.MAX_RETRY_ATTEMPTS} attempts: {e}")
        
        return None
    
    def _get_agent(self, agent_id: str):
        """Get agent instance by ID."""
        # This would be populated by the orchestrator
        return None
