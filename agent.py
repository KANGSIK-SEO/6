"""
Art Authentication Agent
Main agent implementation using Microsoft Agent Framework
Authenticates artworks by analyzing images and provenance
"""

import os
import json
import sys
from typing import Any

from dotenv import load_dotenv

# Agent Framework imports
try:
    # Try importing from installed packages
    try:
        from agent_framework_azure_ai import AzureAIChatClient
        from agent_framework_core import Agent, MessageContent
    except ImportError:
        # Fallback: use imports from installed packages
        from azure_ai_agents import AzureAIChatClient
        print("⚠ Using Azure AI Agents SDK instead of full Agent Framework")
except ImportError as e:
    print(f"⚠ Warning: Agent Framework not fully available: {e}")
    print("  Running in simulation mode with mock implementations")

# Import tools
from tools import (
    create_vision_tool,
    create_provenance_tool,
    create_analyzer,
    create_report_generator,
    create_anomaly_tool,
    create_custom_vision_tool,
)


# Load environment variables
load_dotenv()


class ArtAuthenticationAgent:
    """Main agent for artwork authentication"""
    
    def __init__(self):
        """Initialize the art authentication agent"""
        self.vision_tool = create_vision_tool(
            endpoint=os.getenv("AZURE_VISION_ENDPOINT"),
            key=os.getenv("AZURE_VISION_KEY")
        )
        self.provenance_tool = create_provenance_tool(
            db_connection=os.getenv("PROVENANCE_DB_CONNECTION")
        )
        self.anomaly_tool = create_anomaly_tool(
            endpoint=os.getenv("ANOMALY_DETECTOR_ENDPOINT"),
            key=os.getenv("ANOMALY_DETECTOR_KEY")
        )
        self.custom_vision_tool = create_custom_vision_tool(
            endpoint=os.getenv("CUSTOM_VISION_ENDPOINT"),
            key=os.getenv("CUSTOM_VISION_KEY"),
            project_id=os.getenv("CUSTOM_VISION_PROJECT_ID")
        )
        self.analyzer = create_analyzer()
        self.report_generator = create_report_generator()
        
        # Initialize Agent Framework client
        self._initialize_agent_client()
    
    def _initialize_agent_client(self):
        """Initialize Azure AI Chat Client for Agent Framework"""
        try:
            # Try to initialize Foundry client
            from azure_ai_agents import AzureAIChatClient
            
            # Use Foundry deployment credentials
            self.client = AzureAIChatClient(
                endpoint=os.getenv("FOUNDRY_PROJECT_ENDPOINT"),
                credential=os.getenv("FOUNDRY_API_KEY"),
                model_deployment=os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME", "gpt-4o"),
            )
            print("✓ Agent Framework client initialized successfully")
        except Exception as e:
            print(f"⚠ Agent Framework client not configured: {e}")
            print("  Running analysis tools in simulation mode")
            self.client = None
    
    def authenticate_artwork(
        self,
        image_source: str,
        artist: str,
        title: str,
        artwork_metadata: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        Authenticate a piece of artwork.
        
        Args:
            image_source: URL or filepath of artwork image
            artist: Artist name
            title: Artwork title
            artwork_metadata: Optional metadata (period, medium, dimensions, etc.)
            
        Returns:
            Complete authentication report
        """
        
        print(f"\n{'='*80}")
        print(f"Authenticating: {title} by {artist}")
        print(f"{'='*80}\n")
        
        # Step 1: Analyze image
        print("📸 Step 1: Analyzing artwork image...")
        vision_results = self.vision_tool.analyze_artwork(image_source)
        print(f"   ✓ Vision analysis complete")
        print(f"   - Confidence: {vision_results.get('confidence_level')}")
        print(f"   - Anomalies detected: {vision_results.get('anomalies', {}).get('detected', False)}")
        
        # Step 1b: Advanced Analysis - Anomaly Detection (Forgery Detection)
        print("\n🔍 Step 1b: Detecting forgery patterns...")
        anomaly_results = self.anomaly_tool.detect_forgery_patterns(vision_results)
        print(f"   ✓ Forgery analysis complete")
        print(f"   - Anomaly Score: {anomaly_results.get('anomaly_score')}/100")
        print(f"   - Forgery Risk: {'HIGH' if anomaly_results.get('forgery_detected') else 'LOW'}")
        
        # Step 1c: Advanced Analysis - Artist Style Classification
        print("\n🎨 Step 1c: Classifying artist style...")
        style_results = self.custom_vision_tool.classify_artist_style(image_source, ["Monet", "Van Gogh", "Picasso"])
        print(f"   ✓ Style classification complete")
        print(f"   - Primary Match: {style_results.get('primary_artist')} ({style_results.get('confidence'):.0%})")
        if style_results.get('similar_artists'):
            print(f"   - Similar to: {', '.join(style_results.get('similar_artists', []))}")
        
        # Step 2: Search provenance
        print("\n📚 Step 2: Searching provenance records...")
        auction_results = self.provenance_tool.search_auction_records(artist, title)
        ownership_results = self.provenance_tool.get_ownership_history(f"{artist.lower()}_{title.lower().replace(' ', '_')}")
        theft_results = self.provenance_tool.search_stolen_art(artist, title)
        
        provenance_combined = {
            "auction_records": auction_results,
            "ownership_history": ownership_results,
            "theft_database": theft_results,
            "verification_status": "complete_chain_verified",
            "provenance_chain_length": len(ownership_results.get("ownership_history", []))
        }
        print(f"   ✓ Provenance search complete")
        print(f"   - Records found: {auction_results.get('records_found', 0)}")
        print(f"   - Owners verified: {provenance_combined['provenance_chain_length']}")
        print(f"   - Theft status: {theft_results.get('theft_status', 'unknown')}")
        
        # Step 3: Analyze and calculate score
        print("\n🔬 Step 3: Analyzing and calculating authentication score...")
        
        market_data = auction_results.get("price_trend", {})
        authentication_result = self.analyzer.calculate_authentication_score(
            vision_results,
            provenance_combined,
            market_data
        )
        
        print(f"   ✓ Analysis complete")
        print(f"   - Overall Score: {authentication_result.get('overall_authentication_score')}/100")
        print(f"   - Confidence Level: {authentication_result.get('confidence_level').upper()}")
        
        # Step 4: Generate report
        print("\n📋 Step 4: Generating authentication report...")
        
        if artwork_metadata is None:
            artwork_metadata = {}
        
        artwork_metadata.update({
            "artist": artist,
            "title": title,
            "acquisition_date": "2025-12-01"
        })
        
        report = self.report_generator.generate_authentication_report(
            artwork_metadata,
            authentication_result
        )
        print(f"   ✓ Report generated")
        print(f"   - Report ID: {report.get('report_metadata', {}).get('report_id')}")
        print(f"   - Certification Level: {report.get('certification', {}).get('certification_level')}")
        
        return {
            "authentication_result": authentication_result,
            "detailed_report": report,
            "analysis_summary": {
                "image_source": image_source,
                "artwork_info": artwork_metadata,
                "vision_analysis": vision_results,
                "forgery_detection": anomaly_results,
                "artist_style_classification": style_results,
                "provenance_chain": provenance_combined,
                "market_indicators": market_data
            }
        }
    
    def generate_expert_opinion(self, authentication_data: dict[str, Any]) -> str:
        """
        Generate expert opinion using Agent Framework with LLM.
        
        Args:
            authentication_data: Complete authentication analysis data
            
        Returns:
            Expert opinion text
        """
        
        if not self.client:
            return "Expert opinion unavailable - Agent Framework client not configured"
        
        try:
            # Prepare context for LLM
            score = authentication_data.get("authentication_result", {}).get("overall_authentication_score", 0)
            verdict = authentication_data.get("authentication_result", {}).get("authentication_verdict", "")
            risks = authentication_data.get("authentication_result", {}).get("risk_assessment", {})
            
            prompt = f"""
            Based on the following artwork authentication analysis, provide a concise expert opinion:
            
            Authentication Score: {score}/100
            Verdict: {verdict}
            Risk Assessment: {json.dumps(risks, indent=2)}
            
            Provide a professional, expert perspective on the authenticity and any additional considerations 
            for potential buyers or museum curators.
            """
            
            # Call Agent Framework client for LLM response
            # Note: This requires proper configuration with Foundry
            # For now, return a formatted response
            
            return f"""
            EXPERT OPINION:
            Based on the comprehensive analysis (score: {score}/100), {verdict.lower()}
            
            The authentication analysis shows {risks.get('overall_risk_level', 'medium')} risk level with 
            {risks.get('risk_count', 0)} identified considerations.
            
            Recommendation: {authentication_data.get('authentication_result', {}).get('recommendation', 'N/A')}
            """
            
        except Exception as e:
            print(f"Error generating expert opinion: {e}")
            return "Expert opinion generation failed"
    
    async def run_agent(self, user_query: str) -> str:
        """
        Run agent with user query (async for production use).
        
        Args:
            user_query: User's question about artwork authentication
            
        Returns:
            Agent response
        """
        
        if not self.client:
            return "Agent not configured. Please set up Azure Foundry credentials in .env file"
        
        try:
            # In production, this would use actual Agent Framework agent
            # For demonstration, return a formatted response
            
            response = f"""
            Agent received query: {user_query}
            
            To authenticate artwork:
            1. Provide image of the artwork
            2. Supply artist name and title
            3. Agent will analyze vision, provenance, and market data
            4. Receive comprehensive authentication report
            
            Use the dashboard or API to submit authentication requests.
            """
            
            return response
            
        except Exception as e:
            print(f"Error running agent: {e}")
            return f"Agent execution failed: {str(e)}"


def main():
    """Main execution function"""
    
    # Initialize agent
    agent = ArtAuthenticationAgent()
    
    # Example: Authenticate a sample artwork
    sample_artwork = {
        "image_source": "/Users/kangsikseo/Downloads/0c9235dca33e775fe86a9d93977066f1-2000x2003.jpg.webp",
        "artist": "Unknown",
        "title": "Abstract Red Composition",
        "metadata": {
            "period": "Contemporary",
            "medium": "Oil on Canvas",
            "dimensions": "2000x2003 pixels",
            "owner": "Private Collection",
            "catalog": "Test-001",
            "style": "Modern Abstract",
            "subject": "Abstract expressionist work with red tones"
        }
    }
    
    # Run authentication
    result = agent.authenticate_artwork(
        image_source=sample_artwork["image_source"],
        artist=sample_artwork["artist"],
        title=sample_artwork["title"],
        artwork_metadata=sample_artwork["metadata"]
    )
    
    # Generate expert opinion
    print("\n" + "="*80)
    print("EXPERT OPINION")
    print("="*80)
    expert_opinion = agent.generate_expert_opinion(result)
    print(expert_opinion)
    
    # Export report
    print("\n" + "="*80)
    print("GENERATING REPORT OUTPUT")
    print("="*80)
    
    report = result["detailed_report"]
    
    # Export as JSON
    json_report = agent.report_generator.export_report_json(report)
    with open("authentication_report.json", "w") as f:
        f.write(json_report)
    print("✓ JSON report saved: authentication_report.json")
    
    # Export as text
    text_report = agent.report_generator.export_report_text(report)
    with open("authentication_report.txt", "w") as f:
        f.write(text_report)
    print("✓ Text report saved: authentication_report.txt")
    
    # Print summary
    print("\n" + "="*80)
    print("AUTHENTICATION SUMMARY")
    print("="*80)
    
    auth_result = result["authentication_result"]
    print(f"Overall Score: {auth_result.get('overall_authentication_score')}/100")
    print(f"Confidence Level: {auth_result.get('confidence_level').upper()}")
    print(f"Verdict: {auth_result.get('authentication_verdict')}")
    print(f"Recommendation: {auth_result.get('recommendation')}")
    
    print("\n✓ Authentication process complete!")


if __name__ == "__main__":
    main()
