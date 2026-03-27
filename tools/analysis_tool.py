"""
Authentication Analysis Tool for artwork verification
Calculates authentication score based on multiple factors
"""

from typing import Any
import math


class AuthenticationAnalyzer:
    """Calculates artwork authentication score"""
    
    def __init__(self):
        """Initialize authentication analyzer"""
        self.weights = {
            "vision_analysis": 0.35,
            "provenance_verification": 0.40,
            "market_indicators": 0.15,
            "expert_consistency": 0.10
        }
    
    def calculate_authentication_score(
        self,
        vision_results: dict[str, Any],
        provenance_results: dict[str, Any],
        market_data: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        Calculate comprehensive authentication score.
        
        Args:
            vision_results: Results from vision analysis
            provenance_results: Results from provenance search
            market_data: Optional market indicators
            
        Returns:
            Authentication score and detailed breakdown
        """
        
        # Extract component scores
        vision_score = self._calculate_vision_score(vision_results)
        provenance_score = self._calculate_provenance_score(provenance_results)
        market_score = self._calculate_market_score(market_data)
        expert_score = self._calculate_expert_consistency(vision_results, provenance_results)
        
        # Calculate weighted overall score
        overall_score = (
            vision_score * self.weights["vision_analysis"] +
            provenance_score * self.weights["provenance_verification"] +
            market_score * self.weights["market_indicators"] +
            expert_score * self.weights["expert_consistency"]
        )
        
        # Determine confidence level
        confidence_level = self._determine_confidence(overall_score)
        
        # Generate risk assessment
        risk_assessment = self._generate_risk_assessment(
            vision_results,
            provenance_results,
            overall_score
        )
        
        return {
            "overall_authentication_score": round(overall_score, 2),
            "confidence_level": confidence_level,
            "component_scores": {
                "vision_analysis_score": round(vision_score, 2),
                "provenance_verification_score": round(provenance_score, 2),
                "market_indicators_score": round(market_score, 2),
                "expert_consistency_score": round(expert_score, 2)
            },
            "weight_distribution": self.weights,
            "authentication_verdict": self._generate_verdict(overall_score),
            "risk_assessment": risk_assessment,
            "recommendation": self._generate_recommendation(overall_score, confidence_level)
        }
    
    def _calculate_vision_score(self, vision_results: dict[str, Any]) -> float:
        """Calculate vision analysis component score"""
        if not vision_results:
            return 0.0
        
        # Base score from artifact anomalies
        base_score = 85.0 if not vision_results.get("anomalies", {}).get("detected") else 45.0
        
        # Adjust based on confidence
        confidence_factor = vision_results.get("confidence_level", 0.5)
        style_consistency = vision_results.get("style_markers", {}).get("period_consistency", 0.5) * 100
        brushwork_consistency = vision_results.get("brushwork_analysis", {}).get("consistency_score", 0.5) * 100
        
        # Weighted combination
        score = (base_score * 0.4 + style_consistency * 0.3 + brushwork_consistency * 0.3)
        
        return min(100, max(0, score * confidence_factor))
    
    def _calculate_provenance_score(self, provenance_results: dict[str, Any]) -> float:
        """Calculate provenance verification component score"""
        if not provenance_results:
            return 0.0
        
        # Check theft status
        theft_check = provenance_results.get("theft_status", {})
        if not isinstance(theft_check, dict):
            theft_check = {}
        theft_status = theft_check.get("status", "clear") if isinstance(theft_check, dict) else "clear"
        
        base_score = 95.0 if theft_status == "clear" else 15.0
        
        # Chain completeness
        chain_completeness = provenance_results.get("provenance_chain_length", 3) * 20  # 20 points per verified owner
        chain_completeness = min(100, chain_completeness)
        
        # Verification status
        verification = provenance_results.get("verification_status", "partial") 
        verification_bonus = 10.0 if "verified" in str(verification).lower() else 0.0
        
        score = (base_score * 0.5 + chain_completeness * 0.3 + verification_bonus * 0.2)
        
        return min(100, max(0, score))
    
    def _calculate_market_score(self, market_data: dict[str, Any] = None) -> float:
        """Calculate market indicators component score"""
        if not market_data:
            return 75.0  # Default neutral score
        
        # Price consistency indicators
        price_trajectory = market_data.get("price_trajectory", "stable")
        baseline = 70.0
        
        if "upward" in price_trajectory:
            baseline += 15.0
        elif "downward" in price_trajectory:
            baseline -= 20.0
        
        market_demand = market_data.get("market_demand", "medium")
        if market_demand == "high":
            baseline += 5.0
        elif market_demand == "low":
            baseline -= 10.0
        
        return min(100, max(0, baseline))
    
    def _calculate_expert_consistency(
        self,
        vision_results: dict[str, Any],
        provenance_results: dict[str, Any]
    ) -> float:
        """Calculate consistency between vision and provenance results"""
        
        # Check if both analyses point to same conclusion
        vision_consistent = vision_results.get("anomalies", {}).get("detected") == False
        provenance_verified = "verified" in str(provenance_results.get("verification_status", "")).lower()
        
        if vision_consistent and provenance_verified:
            return 95.0
        elif vision_consistent or provenance_verified:
            return 75.0
        else:
            return 45.0
    
    def _determine_confidence(self, score: float) -> str:
        """Determine confidence level based on score"""
        if score >= 90:
            return "very_high"
        elif score >= 75:
            return "high"
        elif score >= 60:
            return "moderate"
        elif score >= 40:
            return "low"
        else:
            return "very_low"
    
    def _generate_verdict(self, score: float) -> str:
        """Generate authentication verdict"""
        if score >= 85:
            return "AUTHENTICATED - Works appear to be original with high confidence"
        elif score >= 70:
            return "LIKELY AUTHENTIC - Strong evidence of authenticity with minor uncertainties"
        elif score >= 55:
            return "UNCERTAIN - Further investigation recommended"
        elif score >= 40:
            return "SUSPICIOUS - Multiple indicators suggest possible forgery"
        else:
            return "LIKELY FORGED - Strong evidence of inauthenticity"
    
    def _generate_risk_assessment(
        self,
        vision_results: dict[str, Any],
        provenance_results: dict[str, Any],
        overall_score: float
    ) -> dict[str, Any]:
        """Generate detailed risk assessment"""
        
        risks = []
        
        if vision_results.get("anomalies", {}).get("detected"):
            anomalies = vision_results.get("anomalies", {}).get("suspicious_areas", [])
            if anomalies:
                risks.append({
                    "risk_type": "visual_anomalies",
                    "severity": "high" if len(anomalies) > 2 else "medium",
                    "details": anomalies
                })
        
        provenance_chain = provenance_results.get("provenance_chain_length", 0)
        if provenance_chain < 3:
            risks.append({
                "risk_type": "incomplete_provenance",
                "severity": "medium",
                "details": f"Only {provenance_chain} owners verified in chain"
            })
        
        return {
            "risk_count": len(risks),
            "risks": risks,
            "overall_risk_level": "high" if len(risks) > 2 else "medium" if risks else "low"
        }
    
    def _generate_recommendation(self, score: float, confidence: str) -> str:
        """Generate expert recommendation"""
        if score >= 85 and confidence in ["very_high", "high"]:
            return "RECOMMEND FOR ACQUISITION - Proceed with confidence"
        elif score >= 70 and confidence in ["high", "moderate"]:
            return "RECOMMEND WITH CAUTION - Obtain additional expert opinions"
        else:
            return "RECOMMEND FURTHER DUE DILIGENCE - Request independent certification"


def create_analyzer() -> AuthenticationAnalyzer:
    """Factory function to create authentication analyzer"""
    return AuthenticationAnalyzer()
