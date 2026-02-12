# GroundSwell Image Metadata Tool - Project Notes

## Project Overview
AI-powered web application that automatically generates and embeds EXIF, IPTC, and XMP metadata for GroundSwell brand images.

**Location:** `C:\Users\rodol\groundswell-metadata-tool`
**GitHub:** https://github.com/GroundSwellco/metadata-tool
**Vercel:** Deployed (check Vercel dashboard for URL)

## What It Does
1. User uploads an image (JPEG or PNG)
2. AI analyzes the image + filename using vision capabilities
3. Generates metadata based on GroundSwell brand patterns (learned from spreadsheet)
4. User can edit all EXIF, IPTC, XMP fields in tabbed interface
5. Downloads image with metadata embedded

## Tech Stack
- **Backend:** FastAPI (Python)
- **AI:** Anthropic Claude API (vision) - can be switched to OpenAI
- **Metadata:** piexif (EXIF), Pillow (PNG), custom XMP embedding
- **Frontend:** Vanilla HTML/CSS/JS (embedded in api/index.py for Vercel)
- **Deployment:** Vercel (serverless Python)

## File Structure
```
groundswell-metadata-tool/
├── api/
│   ├── index.py          # Vercel serverless function (main app)
│   └── requirements.txt  # Python deps for Vercel
├── app.py                # Local development version
├── templates/
│   └── index.html        # Local dev HTML template
├── vercel.json           # Vercel configuration
├── requirements.txt      # Local Python dependencies
├── .env                  # API keys (not in git)
├── .env.example          # Template for .env
└── CLAUDE.md             # This file
```

## Current Status: DEPLOYED BUT NEEDS FIXES

### Completed
- [x] Core app functionality (upload, AI analysis, metadata writing)
- [x] EXIF, IPTC, XMP metadata support for JPEG and PNG
- [x] Editable metadata fields with tabbed UI
- [x] GitHub repo setup
- [x] Vercel deployment structure

### Issues to Fix
- [ ] **Vercel 500 error** - Check function logs, may need API key setup
- [ ] **API Key** - User needs to set ANTHROPIC_API_KEY in Vercel env vars

### Pending Decisions
- [ ] **AI Provider** - Currently Anthropic, user considering OpenAI GPT-4o as alternative
- [ ] **Database/Storage** - User interested in Supabase for:
  - Saving processed images
  - Keeping metadata history
  - Optional user accounts

## GroundSwell Brand Context
The AI uses this context to generate relevant metadata:
- **Company:** GroundSwell - Business Ownership Platform
- **Key Concepts:** Organizational Alpha, Fractal Flywheel, Changing Pains, etc.
- **Key People:** Bob Bennett, Cody Marshall
- **Contact:** www.groundswell.co, 435-214-2997
- **Categories:** Business Ownership Platform, Organizational Development, Management & Leadership

## Environment Variables Needed
```
ANTHROPIC_API_KEY=sk-ant-...  # For Claude AI
# OR if switching to OpenAI:
OPENAI_API_KEY=sk-...
```

## Quick Commands

### Run Locally
```bash
cd C:\Users\rodol\groundswell-metadata-tool
python app.py
# Opens at http://localhost:8000
```

### Push to GitHub
```bash
cd C:\Users\rodol\groundswell-metadata-tool
git add .
git commit -m "Your message"
git push
```

## Next Steps (Priority Order)
1. Fix Vercel deployment (check logs, verify API key)
2. Decide on AI provider (Anthropic vs OpenAI)
3. Add Supabase integration for image storage
4. Optional: Add user authentication

## Reference Files
- **Metadata patterns learned from:** `C:\Users\rodol\GroundSwell℠MetadataExif,IPTCandXMP.xlsx`
- Contains 96 image entries with full EXIF/IPTC/XMP metadata examples
