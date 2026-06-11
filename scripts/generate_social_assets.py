#!/usr/bin/env python3
"""
NEXUS-14: generate_social_assets.py
scripts/generate_social_assets.py

Standalone script that calls agents/social_video_agent.py logic.
Called directly from produce_article.py and GitHub Actions.

Usage:
  python scripts/generate_social_assets.py

Env vars expected (same as produce_article.py):
  OPENAI_API_KEY, ARTICLE_INDEX, TOPIC_OVERRIDE, TARGET_MARKET
"""
import os
import sys

# Add project root to path so we can import the agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Re-use the social video agent logic directly
if __name__ == "__main__":
    # Import and run the agent
    try:
        # The agent module is self-contained with a main() function
        agent_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agents",
            "social_video_agent.py"
        )
        import importlib.util
        spec = importlib.util.spec_from_file_location("social_video_agent", agent_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
    except Exception as e:
        print(f"ERROR running social_video_agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
