from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, Any, Optional
import tempfile
import json
import os
import base64
from datetime import datetime
from fill_pdf_form import PDFFormFiller

app = FastAPI(
    title="SSA-3373 PDF Form Filler",
    description="API for filling SSA-3373 forms with custom line limits",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your specific Vercel domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FormRequest(BaseModel):
    fields: Dict[str, Any]
    line_limits: Optional[Dict[str, int]] = None
    template_name: Optional[str] = "ssa-3373-formatted-blank.pdf"

class GPTFormRequest(BaseModel):
    template_name: Optional[str] = "ssa-3373-formatted-blank.pdf"
    fields: Dict[str, str]
    
    class Config:
        schema_extra = {
            "example": {
                "template_name": "ssa-3373-formatted-blank.pdf",
                "fields": {
                    "Name[0]": "Sarah Johnson",
                    "SSN[0]": "456-78-9012",
                    "Address[0]": "1245 Maple Street",
                    "City[0]": "Springfield", 
                    "State[0]": "MO",
                    "ZIP[0]": "65807",
                    "Date[0]": "June 18, 2025"
                }
            }
        }

@app.post("/fill-ssa-form-gpt")
async def fill_ssa_form_gpt(request: GPTFormRequest):
    """
    GPT Actions compatible endpoint - returns PDF as downloadable data URL
    """
    try:
        print("=== GPT ENDPOINT CALLED ===")
        print(f"Template: {request.template_name}")
        print(f"Fields count: {len(request.fields)}")
        
        # Validate fields
        if not request.fields or len(request.fields) == 0:
            return {"error": "Missing or empty fields", "status": "error"}, 400
        
        # Generate PDF using existing logic
        pdf_content = await generate_pdf_for_gpt(request.template_name, request.fields)
        
        # Validate PDF was generated
        if not pdf_content or len(pdf_content) < 1000:
            return {"error": "PDF generation failed - no content", "status": "error"}, 500
            
        if not pdf_content.startswith(b'%PDF'):
            return {"error": "Invalid PDF format", "status": "error"}, 500
        
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ssa-3373-filled_{timestamp}.pdf"
        
        # Convert to base64 for GPT Actions
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Create data URL for immediate download
        data_url = f"data:application/pdf;base64,{pdf_base64}"
        
        print(f"=== PDF PROCESSED ===")
        print(f"PDF size: {len(pdf_content)} bytes")
        print(f"Base64 size: {len(pdf_base64)} characters")
        print(f"Filename: {filename}")
        
        return {
            "status": "success",
            "message": "PDF generated successfully and ready for download",
            "filename": filename,
            "download_url": data_url,
            "pdf_size_kb": round(len(pdf_content) / 1024, 1),
            "download_ready": True
        }
        
    except Exception as e:
        print(f"=== ERROR IN GPT ENDPOINT ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to generate PDF"
        }, 500


@app.post("/fill-ssa-form")
async def fill_ssa_form(request: FormRequest):
    """
    Fill SSA-3373 form with provided data and line limits
    
    Args:
        request: FormRequest containing fields, optional line_limits, and template_name
        
    Returns:
        PDF file as download
    """
    try:
        # Get template path
        template_path = os.path.join("templates", request.template_name)
        if not os.path.exists(template_path):
            raise HTTPException(
                status_code=404, 
                detail=f"Template {request.template_name} not found. Available templates: {get_available_templates()}"
            )
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as json_temp:
            json.dump(request.fields, json_temp, indent=2)
            json_temp_path = json_temp.name
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output_temp:
            output_temp_path = output_temp.name
        
        try:
            # Fill the form using your existing PDFFormFiller logic
            with PDFFormFiller(template_path, json_temp_path, output_temp_path) as filler:
                
                # Apply line limits (use provided or default)
                line_limits = request.line_limits or get_default_line_limits()
                filler.set_multiple_field_limits(line_limits)
                
                # Fill and save the form
                filler.fill_form()
                filler.save()
            
            # Read the filled PDF
            with open(output_temp_path, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
            
            return Response(
                content=pdf_content,
                media_type='application/pdf',
                headers={
                    "Content-Disposition": "attachment; filename=filled_ssa-3373.pdf",
                    "Content-Type": "application/pdf",  # Explicit Content-Type
                    "Content-Length": str(len(pdf_content)),  # Critical for GPT Actions
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Access-Control-Expose-Headers": "Content-Disposition, Content-Length",  # Key for CORS
                    "Accept-Ranges": "bytes"  # Helps with large file downloads
                }
            )
            
        finally:
            # Cleanup temporary files
            if os.path.exists(json_temp_path):
                os.unlink(json_temp_path)
            if os.path.exists(output_temp_path):
                os.unlink(output_temp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Form filling failed: {str(e)}")

def get_default_line_limits():
    """Return the default line limits for SSA-3373 form fields"""
    return {
        # Main narrative fields
        "N5text[0]": 7,      # Disability explanation
        "N6text[0]": 4,      # Wake up to bed each day description
        "N7text[0]": 1,      # Take care
        "N9IfYesField[0]": 1, # Yes pets
        "N10Field[0]": 1,     # What could you do that you can't now
        "N11IfYesField[0]": 1, # Sleep
        
        # Personal care activities
        "N12Dress[0]": 1,     # Dressing ability
        "N12Bathe[0]": 1,     # Bathing ability  
        "N12CareForHair[0]": 1, # Hair care ability
        "N12Save[0]": 1,      # Shaving ability
        "N12FeedSelf[0]": 1,  # Feeding ability
        "N12UseTheToilet[0]": 1, # Toilet use ability
        "N12Other[0]": 1,     # Other personal care
        "N12BIfYesField[0]": 2, # Help received with personal care
        "N12CIfYesField[0]": 3, # Changes in personal care abilities
        
        # Meals and Housework
        "N13AIfYesField[0]": 2, # Meals Yes Description
        "N13AHowOftenField[0]": 1, # How often meals
        "N13AHowLong[0]": 1,   # How long taking meals
        "N13AAnyChngsField[0]": 1, # Any changes meals
        "N13BIfNoField[0]": 3, # Meals No Description
        "N14AField[0]": 2,     # Housework
        "N14BField[0]": 1,     # How long housework
        "N14CIfYesField[0]": 1, # Encouraged housework
        "N14dField[0]": 2,     # No housework - why not?
        
        # Transportation and mobility
        "N15A[0]": 1,         # Go Outside
        "N15AIfField[0]": 2,   # Why stopped driving
        "N15CIfNoField[0]": 2, # Public transportation availability
        "N15DIfYouDontDrive[0]": 2, # Transportation alternatives
        
        # Shopping and money management
        "N16B[0]": 1,         # Shopping information
        "N16C[0]": 1,         # Shopping limitations
        "N17AExplain[0]": 2,   # Money handling explanation
        "N17BIfYes[0]": 4,     # Changes in money management
        
        # Hobbies
        "N18A[0]": 3,         # Hobbies overview
        "N18B[0]": 2,         # Hobby frequency
        "N18C[0]": 2,         # Hobby changes
        
        # Social activities and going out
        "N15BOtherField[0]": 1, # Other transportation ability
        "N19A[0]": 1,         # Explain other social activities
        "N19B[0]": 1,         # 19c - list things on regular basis
        "N19BHowOften[0]": 2,  # 19c Yes on need someone to accompany
        "N19CIfYes[0]": 2,     # 19d Yes on problems with social activities
        "N19D[0]": 2,         # 19e Describe any changes in social activities
        
        # Physical and cognitive limitations
        "N20A[0]": 3,         # Physical limitations description
        "N20C[0]": 1,         # Distance before stop and rest
        "N20CIfYou[0]": 2,     # Rest time
        "N20D[0]": 2,         # Cognitive/mental limitations
        "N20F[0]": 2,         # How long follow instructions
        "N20G[0]": 2,         # How well spoken instructions
        "N20H[0]": 2,         # How well authority
        
        # Work history details
        "N20IIfYesExplain[0]": 4, # Fired for problems getting along with others
        "N20IIfYesEmployer[0]": 1, # Employer information
        "N20J[0]": 1,         # Handle Stress
        "N20K[0]": 2,         # Handle Change in Routine
        "N20LIfYes[0]": 9,     # Unusual Behavior
        
        # Assistive devices and equipment
        "N21IfOther[0]": 1,    # Other assistive devices
        "N21Which[0]": 2,      # Which rx by doctor
        "N21WhenPrescribed[0]": 2, # When rx by doctor
        "N21WhenDoYou[0]": 7,   # When do you need to use
        
        # Medication details
        "N22Med1[0]": 1,       # Medication 1 name
        "N22Effects1[0]": 1,   # Medication 1 side effects
        "N22Med2[0]": 1,       # Medication 2 name
        "N22Effects2[0]": 1,   # Medication 2 side effects
        "N22Med3[0]": 1,       # Medication 3 name
        "N22Effects3[0]": 1,   # Medication 3 side effects
        "N22Med4[0]": 1,       # Medication 4 name
        "N22Effects4[0]": 1,   # Medication 4 side effects
        "N22Med5[0]": 1,       # Medication 5 name
        "N22Effects5[0]": 1,   # Medication 5 side effects
        
        # Final remarks and additional information
        "Remarks[0]": 13,       # Additional information/remarks
    }

def get_available_templates():
    """Get list of available PDF templates"""
    template_dir = "templates"
    if os.path.exists(template_dir):
        return [f for f in os.listdir(template_dir) if f.endswith('.pdf')]
    return []

async def generate_pdf_for_gpt(template_name: str, fields: dict) -> bytes:
    """
    Generate PDF using existing PDFFormFiller logic - for GPT endpoint
    """
    try:
        # Get template path
        template_path = os.path.join("templates", template_name)
        if not os.path.exists(template_path):
            raise Exception(f"Template {template_name} not found. Available: {get_available_templates()}")
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as json_temp:
            json.dump(fields, json_temp, indent=2)
            json_temp_path = json_temp.name
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output_temp:
            output_temp_path = output_temp.name
        
        try:
            # Fill the form using your existing PDFFormFiller logic
            with PDFFormFiller(template_path, json_temp_path, output_temp_path) as filler:
                
                # Apply default line limits
                line_limits = get_default_line_limits()
                filler.set_multiple_field_limits(line_limits)
                
                # Fill and save the form
                filler.fill_form()
                filler.save()
            
            # Read the filled PDF
            with open(output_temp_path, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
                
            return pdf_content
            
        finally:
            # Cleanup temporary files
            if os.path.exists(json_temp_path):
                os.unlink(json_temp_path)
            if os.path.exists(output_temp_path):
                os.unlink(output_temp_path)
                
    except Exception as e:
        print(f"PDF generation error: {e}")
        raise Exception(f"PDF generation failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "SSA-3373 PDF Form Filler",
        "version": "1.0.0"
    }

@app.get("/form-info")
async def get_form_info():
    """Debug endpoint to see available templates and configuration info"""
    templates = get_available_templates()
    
    return {
        "available_templates": templates,
        "default_template": "ssa-3373-formatted-blank.pdf",
        "default_line_limits_count": len(get_default_line_limits()),
        "api_endpoints": {
            "fill_form": "/fill-ssa-form",
            "fill_form_gpt": "/fill-ssa-form-gpt",
            "health": "/health",
            "form_info": "/form-info",
            "docs": "/docs"
        },
        "template_directory": "templates/",
        "supported_methods": ["POST /fill-ssa-form", "POST /fill-ssa-form-gpt"]
    }

@app.get("/line-limits")
async def get_line_limits():
    """Get the default line limits configuration"""
    return {
        "default_line_limits": get_default_line_limits(),
        "total_fields_with_limits": len(get_default_line_limits()),
        "description": "These are the default line limits applied to multiline fields in the SSA-3373 form"
    }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "SSA-3373 PDF Form Filler API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/health",
        "form_info": "/form-info",
        "main_endpoint": "/fill-ssa-form"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
