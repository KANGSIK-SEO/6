#!/usr/bin/env python3
"""
Validation script for Azure Art Authentication Agent configuration
Checks .env file and Azure connectivity
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def validate_env():
    """Validate environment configuration"""
    
    print("\n" + "="*80)
    print("🔍 ART AUTHENTICATION AGENT - ENV VALIDATION")
    print("="*80 + "\n")
    
    # Load .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    print(f"✅ .env file found at: {env_path.absolute()}")
    
    # Load environment variables
    load_dotenv()
    
    # Check Azure Vision configuration
    print("\n" + "-"*80)
    print("📸 AZURE VISION CONFIGURATION")
    print("-"*80)
    
    vision_endpoint = os.getenv("AZURE_VISION_ENDPOINT")
    vision_key = os.getenv("AZURE_VISION_KEY")
    
    if vision_endpoint:
        print(f"✅ AZURE_VISION_ENDPOINT: {vision_endpoint}")
    else:
        print("❌ AZURE_VISION_ENDPOINT: NOT SET")
        return False
    
    if vision_key:
        masked_key = vision_key[:10] + "***" + vision_key[-10:]
        print(f"✅ AZURE_VISION_KEY: {masked_key}")
    else:
        print("❌ AZURE_VISION_KEY: NOT SET")
        return False
    
    # Check region
    region = os.getenv("AZURE_REGION", "eastus")
    print(f"✅ AZURE_REGION: {region}")
    
    # Check Foundry configuration (optional)
    print("\n" + "-"*80)
    print("🤖 MICROSOFT FOUNDRY CONFIGURATION (Optional)")
    print("-"*80)
    
    foundry_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    foundry_key = os.getenv("FOUNDRY_API_KEY")
    
    if foundry_endpoint and foundry_key:
        print(f"✅ FOUNDRY_PROJECT_ENDPOINT: {foundry_endpoint}")
        masked_foundry_key = foundry_key[:10] + "***" + foundry_key[-10:]
        print(f"✅ FOUNDRY_API_KEY: {masked_foundry_key}")
        print("🎯 Foundry is configured - LLM expert opinions will be enabled")
    else:
        print("⚠️  Foundry not fully configured (optional)")
        print("   → Expert opinion generation will use simulation mode")
    
    # Test Azure Connection
    print("\n" + "-"*80)
    print("🔗 TESTING AZURE CONNECTIVITY")
    print("-"*80)
    
    try:
        import httpx
        
        headers = {
            "Ocp-Apim-Subscription-Key": vision_key,
            "Content-Type": "application/json"
        }
        
        # Use Azure Vision Analyze endpoint
        url = f"{vision_endpoint.rstrip('/')}/vision/v3.2/analyze"
        
        # Test with correct visual features for v3.2
        test_params = {
            "visualFeatures": "color,objects,tags,description",
        }
        
        test_data = {"url": "https://upload.wikimedia.org/wikipedia/commons/6/6d/Good_Food_Display_-_NCI_Visuals_Online.jpg"}
        
        print(f"📡 Attempting connection to: {url}")
        print(f"   Testing with sample image URL...")
        
        with httpx.Client() as client:
            response = client.post(
                url,
                json=test_data,
                headers=headers,
                params=test_params,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Azure Vision API is RESPONDING")
                result = response.json()
                print(f"  Response: {result.get('colors', 'Data received')}")
                print(f"  Connection status: SUCCESS ✓")
            elif response.status_code == 401:
                print("❌ Authentication failed - invalid API key")
                print(f"   Status: {response.status_code}")
                print(f"   Check AZURE_VISION_KEY is correct")
                return False
            elif response.status_code == 404:
                print("❌ Endpoint not found")
                print(f"   Status: {response.status_code}")
                print(f"   Check AZURE_VISION_ENDPOINT is correct")
                return False
            else:
                print(f"❌ Unexpected response: {response.status_code}")
                print(f"   Body: {response.text[:200]}")
                return False
                
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        print(f"   This could be due to network issues or invalid endpoint")
        return False
    
    # Summary
    print("\n" + "="*80)
    print("✅ VALIDATION COMPLETE - ALL CHECKS PASSED")
    print("="*80)
    print("\n🎯 Environment is configured correctly!")
    print("✨ Art Authentication Agent is ready to use Real Azure Vision API\n")
    
    return True


if __name__ == "__main__":
    success = validate_env()
    sys.exit(0 if success else 1)
