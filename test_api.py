#!/usr/bin/env python3
"""
Test script for the SSA-3373 PDF Form Filler API
Usage: python test_api.py [json_file] [api_url]
"""

import requests
import json
import sys
from datetime import datetime
import os

def test_api(json_file=None, api_url=None):
    """Test the SSA-3373 API with sample or provided data"""
    
    # Default API URL (update with your Railway URL)
    if not api_url:
        api_url = "https://your-app.railway.app"  # Update this with your actual Railway URL
    
    # Sample test data if no file provided
    if not json_file:
        print("🧪 Using sample test data...")
        test_data = {
            "fields": {
                "N5text[0]": "Chronic back pain and severe depression affecting my ability to work and perform daily activities. Pain is constant and worsens with movement.",
                "N6text[0]": "Wake up at 7am with severe pain. Take medications. Rest frequently throughout the day due to fatigue and pain.",
                "N7text[0]": "Need help with household tasks",
                "firstName": "John",
                "lastName": "Doe",
                "N12Dress[0]": "Difficult due to back pain",
                "N12Bathe[0]": "Need to sit while bathing",
                "N13AIfYesField[0]": "Can prepare simple meals but need frequent breaks",
                "N20A[0]": "Cannot lift more than 10 pounds. Walking limited to 1 block. Severe back pain affects all physical activities.",
                "Remarks[0]": "Additional information: Patient has been under medical care for chronic conditions since 2020. Multiple specialists consulted. Treatment includes physical therapy and medication management."
            },
            "line_limits": {
                "N5text[0]": 5,
                "N6text[0]": 3,
                "Remarks[0]": 10
            },
            "template_name": "ssa-3373-formatted-blank.pdf"
        }
    else:
        print(f"📄 Loading data from {json_file}...")
        try:
            with open(json_file, 'r') as f:
                form_data = json.load(f)
            test_data = {
                "fields": form_data,
                "template_name": "ssa-3373-formatted-blank.pdf"
            }
        except Exception as e:
            print(f"❌ Error loading JSON file: {e}")
            return False
    
    print(f"🚀 Testing API at: {api_url}")
    
    # Test health endpoint first
    try:
        print("\n1️⃣ Testing health endpoint...")
        health_response = requests.get(f"{api_url}/health", timeout=10)
        if health_response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {health_response.json()}")
        else:
            print(f"❌ Health check failed: {health_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("💡 Make sure your Railway app is deployed and the URL is correct")
        return False
    
    # Test form info endpoint
    try:
        print("\n2️⃣ Testing form info endpoint...")
        info_response = requests.get(f"{api_url}/form-info", timeout=10)
        if info_response.status_code == 200:
            info_data = info_response.json()
            print("✅ Form info retrieved")
            print(f"   Available templates: {info_data.get('available_templates', [])}")
            print(f"   Default line limits: {info_data.get('default_line_limits_count', 0)} fields")
        else:
            print(f"⚠️  Form info warning: {info_response.status_code}")
    except Exception as e:
        print(f"⚠️  Form info error: {e}")
    
    # Test PDF generation
    try:
        print("\n3️⃣ Testing PDF generation...")
        pdf_response = requests.post(
            f"{api_url}/fill-ssa-form",
            json=test_data,
            timeout=30  # PDF generation might take longer
        )
        
        if pdf_response.status_code == 200:
            # Save the PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_ssa_form_{timestamp}.pdf"
            
            with open(filename, 'wb') as f:
                f.write(pdf_response.content)
            
            file_size = os.path.getsize(filename)
            print("✅ PDF generated successfully!")
            print(f"   📄 Saved as: {filename}")
            print(f"   📊 File size: {file_size:,} bytes")
            
            return True
        else:
            print(f"❌ PDF generation failed: {pdf_response.status_code}")
            try:
                error_detail = pdf_response.json()
                print(f"   Error details: {error_detail}")
            except:
                print(f"   Error response: {pdf_response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - PDF generation took too long")
        return False
    except Exception as e:
        print(f"❌ PDF generation error: {e}")
        return False

def main():
    """Main function"""
    print("=== SSA-3373 API Test Script ===")
    
    # Parse command line arguments
    json_file = sys.argv[1] if len(sys.argv) > 1 else None
    api_url = sys.argv[2] if len(sys.argv) > 2 else None
    
    if json_file and not os.path.exists(json_file):
        print(f"❌ Error: JSON file not found: {json_file}")
        return
    
    # Run the test
    success = test_api(json_file, api_url)
    
    if success:
        print("\n🎉 All tests passed! Your API is working correctly.")
        print("\n💡 Next steps:")
        print("   1. Update the API URL in this script with your actual Railway URL")
        print("   2. Test with your real form data")
        print("   3. Integrate with your Vercel frontend")
    else:
        print("\n💔 Some tests failed. Check the errors above.")
        print("\n🔧 Troubleshooting:")
        print("   1. Verify your Railway app is deployed and running")
        print("   2. Check the Railway logs for errors")
        print("   3. Ensure all required files are uploaded to GitHub")
        print("   4. Verify the API URL is correct")

if __name__ == "__main__":
    main()
