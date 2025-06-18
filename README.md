# SSA-3373 PDF Form Filler API

A FastAPI application for filling SSA-3373 forms with custom line limits, deployed on Railway.

## Files Included

```
railway-app/
├── main.py                              # FastAPI application
├── fill_pdf_form.py                     # PDFFormFiller class (REQUIRED)
├── requirements.txt                     # Python dependencies
├── railway.toml                         # Railway configuration
├── README.md                            # This file
└── templates/
    └── ssa-3373-formatted-blank.pdf     # Your PDF template (REQUIRED)
```

## Setup Instructions

### 1. Add Your Files
You need to add these files to your GitHub repository:

- **`fill_pdf_form.py`** - Your existing PDFFormFiller class
- **`ssa-3373-formatted-blank.pdf`** - Your PDF template (place in `templates/` folder)

### 2. Deploy to Railway

1. Create a new GitHub repository
2. Upload all files from this package
3. Go to [railway.app](https://railway.app)
4. Click "Deploy Now" → "Deploy from GitHub repo"
5. Select your repository
6. Railway will automatically deploy!

### 3. Get Your API URL

After deployment, Railway will provide you with a URL like:
`https://your-app-name.railway.app`

## API Endpoints

### POST /fill-ssa-form
Fill an SSA-3373 form with provided data.

**Request Body:**
```json
{
  "fields": {
    "N5text[0]": "Chronic back pain and depression affecting daily activities...",
    "N6text[0]": "Wake up at 7am, take medications, rest frequently...",
    "firstName": "John",
    "lastName": "Doe"
  },
  "line_limits": {
    "N5text[0]": 7,
    "N6text[0]": 4
  },
  "template_name": "ssa-3373-formatted-blank.pdf"
}
```

**Response:** PDF file download

### GET /health
Health check endpoint

### GET /form-info
Get information about available templates and configuration

### GET /line-limits
Get default line limits configuration

### GET /docs
FastAPI automatic documentation

## Usage Examples

### Command Line (curl)
```bash
curl -X POST https://your-app.railway.app/fill-ssa-form \
  -H "Content-Type: application/json" \
  -d @your_form_data.json \
  --output filled_ssa_form.pdf
```

### From Vercel Frontend
```javascript
const generateForm = async (formData) => {
    const response = await fetch('https://your-app.railway.app/fill-ssa-form', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            fields: formData,
            line_limits: {
                "N5text[0]": 7,
                "N6text[0]": 4
                // ... other limits
            }
        })
    });
    
    if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'filled_ssa_form.pdf';
        a.click();
    }
};
```

### Python Script
```python
import requests
import json

def fill_ssa_form(data_file):
    with open(data_file, 'r') as f:
        form_data = json.load(f)
    
    response = requests.post(
        'https://your-app.railway.app/fill-ssa-form',
        json={"fields": form_data}
    )
    
    if response.status_code == 200:
        with open('filled_form.pdf', 'wb') as f:
            f.write(response.content)
        print("✅ Form generated successfully!")

# Usage
fill_ssa_form('complete_test_data.json')
```

## Default Line Limits

The API includes comprehensive default line limits for all SSA-3373 multiline fields:

- **Main narrative fields**: N5text (7 lines), N6text (4 lines)
- **Personal care activities**: 1-3 lines per field
- **Meals and housework**: 1-3 lines per field
- **Transportation**: 1-2 lines per field
- **Social activities**: 1-2 lines per field
- **Physical/cognitive limitations**: 1-9 lines per field
- **Medications**: 1 line per field
- **Remarks**: 13 lines

You can override any of these by providing custom `line_limits` in your request.

## Environment Variables

No environment variables required for basic operation.

## Support

- Check `/docs` for interactive API documentation
- Use `/health` to verify service status
- Use `/form-info` to see available templates and configuration

## Development

To run locally:
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` for interactive documentation.
