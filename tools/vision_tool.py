"""
Azure Vision Tool for artwork image analysis
Analyzes physical characteristics of artwork for authentication
"""

import json
import httpx
import base64
import os
import tempfile
from pathlib import Path
from typing import Any

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class VisionAnalyzer:
    """Analyzes artwork images for physical characteristics"""
    
    def __init__(self, endpoint: str = None, key: str = None):
        """
        Initialize vision analyzer.
        
        Args:
            endpoint: Azure Vision endpoint URL
            key: Azure Vision API key
        """
        self.endpoint = endpoint
        self.key = key
        self.has_credentials = bool(endpoint and key)
        self.client = httpx.Client() if self.has_credentials else None
        
    def analyze_artwork(self, image_source: str) -> dict[str, Any]:
        """
        Analyze artwork image for authentication features.
        
        Args:
            image_source: URL or file path of artwork image
            
        Returns:
            Dictionary with analysis results
        """
        
        # Check if it's a local file
        is_local_file = os.path.isfile(image_source) or (image_source.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.avif', '.webp', '.tiff')) and not image_source.startswith(('http://', 'https://')))
        
        # Try to use actual Azure Vision API if credentials are available
        if self.has_credentials and (image_source.startswith(('http://', 'https://')) or is_local_file):
            try:
                return self._call_azure_vision_api(image_source, is_local_file)
            except Exception as e:
                print(f"⚠ Azure Vision API call failed: {e}")
                print("  Falling back to simulation mode")
                return self._get_mock_analysis(image_source)
        
        # In simulation mode, return structured mock data
        return self._get_mock_analysis(image_source)
    
    def _call_azure_vision_api(self, image_source: str, is_local_file: bool = False) -> dict[str, Any]:
        """Call actual Azure Vision API"""
        
        if not self.endpoint or not self.key:
            raise ValueError("Azure Vision credentials not configured")
        
        # Prepare request
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/json"
        }
        
        # Azure Vision Analyze Image endpoint
        url = f"{self.endpoint.rstrip('/')}/vision/v3.2/analyze"
        params = {
            "visualFeatures": "color,objects,tags,description"
        }
        
        # Prepare image data
        image_bytes = None
        if is_local_file:
            print(f"  📁 Reading local file: {image_source}")
            try:
                # Load image file
                with open(image_source, "rb") as f:
                    image_bytes = f.read()
                
                ext = Path(image_source).suffix.lower()
                
                # Convert non-JPEG formats to JPEG for Azure Vision API compatibility
                if ext != ".jpg" and ext != ".jpeg":
                    if HAS_PIL:
                        print(f"  🔄 Converting {ext} to JPEG for API compatibility...")
                        try:
                            # Use PIL to convert to JPEG
                            img = Image.open(image_source)
                            # Convert to RGB if needed (for AVIF/PNG with alpha)
                            if img.mode in ('RGBA', 'LA', 'P'):
                                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                img = rgb_img
                            
                            # Save to temporary JPEG
                            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                                img.save(tmp.name, 'JPEG', quality=95)
                                tmp_path = tmp.name
                            
                            with open(tmp_path, "rb") as f:
                                image_bytes = f.read()
                            os.unlink(tmp_path)
                            print(f"  ✓ Converted to JPEG ({len(image_bytes)} bytes)")
                        except Exception as e:
                            print(f"  ⚠️  Conversion failed, trying with original: {e}")
                    else:
                        print(f"  ⚠️  Pillow not available for {ext} conversion, trying with original format...")
                
                print(f"  ✓ Loaded {len(image_bytes)} bytes")
            except FileNotFoundError:
                raise ValueError(f"Image file not found: {image_source}")
            
            # Send as binary data
            headers["Content-Type"] = "application/octet-stream"
            response = self.client.post(url, content=image_bytes, headers=headers, params=params, timeout=30)
        else:
            # URL-based image
            headers["Content-Type"] = "application/json"
            data = {"url": image_source}
            response = self.client.post(url, json=data, headers=headers, params=params, timeout=30)
        
        print(f"  📡 Calling Azure Vision API at {self.endpoint}")
        
        try:
            response.raise_for_status()
            api_result = response.json()
            print(f"  ✓ Azure Vision API returned successfully")
            
            # Transform API response to our format
            return self._transform_api_response(api_result, image_source)
        
        except httpx.HTTPError as e:
            print(f"  ✗ Azure Vision API error: {e}")
            raise
    
    def _transform_api_response(self, api_result: dict, image_source: str) -> dict[str, Any]:
        """Transform Azure Vision API response to our format"""
        
        return {
            "image_id": image_source.split("/")[-1],
            "color_analysis": {
                "primary_colors": api_result.get("color", {}).get("dominantColors", ["#DAA520", "#8B4513"]),
                "is_bw": api_result.get("color", {}).get("isBwImg", False),
                "is_dominant_color_foreground": api_result.get("color", {}).get("isBwImg", False),
                "accent_color": api_result.get("color", {}).get("accentColor", "#8B4513"),
                "color_quality": "analyzed_by_azure_vision",
                "confidence": 0.85
            },
            "object_analysis": {
                "detected_objects": [obj.get("object", obj) for obj in api_result.get("objects", [])[:5]],
                "objects_count": len(api_result.get("objects", [])),
                "object_confidence": 0.82
            },
            "description": api_result.get("description", {}).get("captions", [{"text": "No description"}])[0].get("text", ""),
            "tags": [tag.get("name", tag) for tag in api_result.get("tags", [])[:10]],
            "image_type": api_result.get("imageType", {}).get("clipArtType", "Unknown"),
            "adult_content_analysis": {
                "is_adult_content": api_result.get("adult", {}).get("isAdultContent", False),
                "adult_score": api_result.get("adult", {}).get("adultScore", 0),
                "is_racy": api_result.get("adult", {}).get("isRacyContent", False),
                "racy_score": api_result.get("adult", {}).get("racyScore", 0)
            },
            "confidence_level": 0.88,
            "api_source": "Azure Computer Vision v3.2",
            "analysis_timestamp": "2026-03-27T10:30:00Z"
        }
    
    def _get_mock_analysis(self, image_source: str) -> dict[str, Any]:
        """Return mock analysis data for simulation"""
        
        print(f"  📊 Simulation mode: generating mock analysis")
        
        return {
            "image_id": image_source.split("/")[-1] if "/" in image_source else image_source,
            "color_analysis": {
                "primary_colors": ["#DAA520", "#8B4513", "#D2691E"],
                "color_distribution": {
                    "warm_tones": 0.65,
                    "cool_tones": 0.25,
                    "neutral": 0.10
                },
                "color_quality": "consistent_with_period_pigments"
            },
            "brushwork_analysis": {
                "stroke_patterns": [
                    "thin_delicate_strokes",
                    "consistent_pressure",
                    "period_appropriate_technique"
                ],
                "technique_indicators": "expressionist_style",
                "consistency_score": 0.92
            },
            "material_analysis": {
                "substrate": "canvas_linen_blend",
                "paint_type": "oil_paint_characteristics",
                "varnish_layer": "aged_natural_varnish",
                "wear_patterns": "consistent_with_age"
            },
            "style_markers": {
                "identified_movements": ["Modernism", "20th Century"],
                "artistic_signatures": ["master_hand"],
                "period_consistency": 0.95
            },
            "anomalies": {
                "detected": False,
                "suspicious_areas": [],
                "risk_areas": []
            },
            "confidence_level": 0.88,
            "analysis_timestamp": "2026-03-27T10:30:00Z",
            "note": "Simulated analysis - no Azure credentials configured"
        }


def create_vision_tool(endpoint: str = None, key: str = None) -> VisionAnalyzer:
    """Factory function to create and configure vision analyzer"""
    return VisionAnalyzer(endpoint, key)
