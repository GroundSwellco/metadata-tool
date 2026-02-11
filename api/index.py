import os
import base64
import json
import uuid
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import piexif
import anthropic

app = FastAPI(title="GroundSwell℠ Image Metadata Tool")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# In-memory storage for uploaded files (temporary for serverless)
file_storage = {}

# GroundSwell metadata template
GROUNDSWELL_CONTEXT = """
You are a metadata specialist for GroundSwell℠, a Business Ownership Platform company.

GroundSwell℠ focuses on:
- Organizational Alpha (combined incremental returns and decreased risks)
- Fractal Flywheel of Organizational Development℠
- Fractal Flywheel of Management & Leadership Development℠
- Changing Pains℠ (growing pains when organization's systems don't support its size)
- Stages of Organizational Development℠
- Business Ownership School℠
- Inner Optimization℠
- Pyramid of Tech Stack Development℠
- Direct Ownership

Key people: Bob Bennett, Cody Marshall

Common keywords include: equity partners, strategic partners, return on investment, business building partner,
investment partner, Groundswell, organizational strategies, business growth, risk management, performance enhancement,
business efficiency, strategic management, value creation, operational efficiency, fractal flywheel, flywheel,
business improvement, business advice, business partner, business valuation, private equity

Categories: Business Ownership Platform, Direct Ownership, Organizational Development, Management & Leadership Development

Contact info:
- Website: www.groundswell.co
- Phone: 435-214-2997
- Credit: GroundSwell
- Copyright Status: Protected
"""

METADATA_PROMPT = """
Based on the image filename and visual content, generate metadata for this GroundSwell℠ image.

Filename: {filename}

Generate the following metadata in JSON format:
{{
    "title": "The title/name of the concept shown (from filename or image)",
    "headline": "A brief compelling headline (1 sentence) describing the value proposition",
    "description": "A detailed 2-3 sentence description of the concept",
    "keywords": ["list", "of", "relevant", "keywords", "comma", "separated"],
    "category": "Business Ownership Platform",
    "supplemental_category": "The specific sub-category (e.g., Organizational Development, Management & Leadership Development, Direct Ownership, etc.)",
    "create_date": "{current_date}"
}}

Important:
- The title should match the concept name from the filename (remove file extension, clean up formatting)
- The headline should convey the business value
- The description should explain what the concept means and its importance to businesses
- Keywords should include: the concept name, GroundSwell, relevant business terms, Bob Bennett, Cody Marshall if applicable
- Base your response on the visual content and the GroundSwell context provided

{context}

Return ONLY the JSON object, no additional text.
"""


class SaveMetadataRequest(BaseModel):
    file_id: str
    metadata: dict


def get_media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    return media_types.get(ext, "image/jpeg")


async def analyze_image_with_claude(image_data: bytes, filename: str) -> dict:
    """Use Claude to analyze the image and generate metadata."""

    base64_image = base64.standard_b64encode(image_data).decode("utf-8")
    media_type = get_media_type(filename)
    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = METADATA_PROMPT.format(
        filename=filename,
        current_date=current_date,
        context=GROUNDSWELL_CONTEXT
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ],
    )

    response_text = message.content[0].text

    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    clean_name = Path(filename).stem.replace("-", " ").replace("_", " ").title()
    return {
        "title": clean_name,
        "headline": f"Learn about {clean_name} with GroundSwell℠",
        "description": f"{clean_name} is a key concept in the GroundSwell℠ Business Ownership Platform.",
        "keywords": [clean_name, "GroundSwell", "business", "organizational development"],
        "category": "Business Ownership Platform",
        "supplemental_category": "General",
        "create_date": datetime.now().strftime("%Y-%m-%d")
    }


def create_xmp_packet(metadata: dict) -> str:
    """Create XMP metadata packet as XML string."""
    title = metadata.get('xmp_title', '')
    description = metadata.get('xmp_description', '')
    creator = metadata.get('xmp_creator', 'GroundSwell')
    rights = metadata.get('xmp_rights', '')
    subject = metadata.get('xmp_subject', '')
    headline = metadata.get('xmp_headline', '')
    credit = metadata.get('xmp_credit', 'GroundSwell')
    source = metadata.get('xmp_source', 'GroundSwell')
    date_created = metadata.get('xmp_date_created', '')
    category = metadata.get('xmp_category', 'Business Ownership Platform')

    keywords = [kw.strip() for kw in subject.split(',') if kw.strip()]
    keywords_xml = '\n'.join([f'                        <rdf:li>{kw}</rdf:li>' for kw in keywords])

    xmp = f'''<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="GroundSwell Metadata Tool">
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about=""
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:xmp="http://ns.adobe.com/xap/1.0/"
            xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/"
            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
            xmlns:Iptc4xmpCore="http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/">

            <dc:title>
                <rdf:Alt>
                    <rdf:li xml:lang="x-default">{title}</rdf:li>
                </rdf:Alt>
            </dc:title>

            <dc:description>
                <rdf:Alt>
                    <rdf:li xml:lang="x-default">{description}</rdf:li>
                </rdf:Alt>
            </dc:description>

            <dc:creator>
                <rdf:Seq>
                    <rdf:li>{creator}</rdf:li>
                </rdf:Seq>
            </dc:creator>

            <dc:rights>
                <rdf:Alt>
                    <rdf:li xml:lang="x-default">{rights}</rdf:li>
                </rdf:Alt>
            </dc:rights>

            <dc:subject>
                <rdf:Bag>
{keywords_xml}
                </rdf:Bag>
            </dc:subject>

            <photoshop:Headline>{headline}</photoshop:Headline>
            <photoshop:Credit>{credit}</photoshop:Credit>
            <photoshop:Source>{source}</photoshop:Source>
            <photoshop:DateCreated>{date_created}</photoshop:DateCreated>
            <photoshop:Category>{category}</photoshop:Category>

            <xmpRights:Marked>True</xmpRights:Marked>

            <Iptc4xmpCore:CreatorContactInfo>
                <rdf:Description>
                    <Iptc4xmpCore:CiUrlWork>{metadata.get('xmp_website', 'www.groundswell.co')}</Iptc4xmpCore:CiUrlWork>
                    <Iptc4xmpCore:CiTelWork>{metadata.get('xmp_phone', '435-214-2997')}</Iptc4xmpCore:CiTelWork>
                </rdf:Description>
            </Iptc4xmpCore:CreatorContactInfo>

        </rdf:Description>
    </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''

    return xmp


def process_jpeg_metadata(image_data: bytes, metadata: dict) -> bytes:
    """Process JPEG and add metadata, return bytes."""
    img = Image.open(BytesIO(image_data))

    try:
        exif_dict = piexif.load(img.info.get('exif', b''))
    except:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    artist = metadata.get('exif_artist', 'GroundSwell')
    copyright_text = metadata.get('exif_copyright', '')
    description = metadata.get('exif_description', '')

    exif_dict['0th'][piexif.ImageIFD.Artist] = artist.encode('utf-8')
    exif_dict['0th'][piexif.ImageIFD.Copyright] = copyright_text.encode('utf-8')
    exif_dict['0th'][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')

    user_comment = metadata.get('exif_user_comment', '')
    user_comment_bytes = b'ASCII\x00\x00\x00' + user_comment.encode('utf-8')
    exif_dict['Exif'][piexif.ExifIFD.UserComment] = user_comment_bytes

    exif_bytes = piexif.dump(exif_dict)

    output = BytesIO()
    img.save(output, 'JPEG', exif=exif_bytes, quality=95)
    jpeg_data = output.getvalue()

    # Embed XMP
    xmp_data = create_xmp_packet(metadata)
    xmp_marker = b'\xff\xe1'
    xmp_header = b'http://ns.adobe.com/xap/1.0/\x00'
    xmp_bytes = xmp_data.encode('utf-8')

    segment_length = 2 + len(xmp_header) + len(xmp_bytes)
    length_bytes = segment_length.to_bytes(2, 'big')

    xmp_segment = xmp_marker + length_bytes + xmp_header + xmp_bytes
    final_data = jpeg_data[:2] + xmp_segment + jpeg_data[2:]

    return final_data


def process_png_metadata(image_data: bytes, metadata: dict) -> bytes:
    """Process PNG and add metadata, return bytes."""
    img = Image.open(BytesIO(image_data))

    pnginfo = PngInfo()
    pnginfo.add_text("Title", metadata.get('xmp_title', ''))
    pnginfo.add_text("Description", metadata.get('xmp_description', ''))
    pnginfo.add_text("Author", metadata.get('exif_artist', 'GroundSwell'))
    pnginfo.add_text("Copyright", metadata.get('exif_copyright', ''))
    pnginfo.add_text("Comment", metadata.get('exif_user_comment', ''))
    pnginfo.add_text("Keywords", metadata.get('iptc_keywords', ''))
    pnginfo.add_text("Headline", metadata.get('iptc_headline', ''))
    pnginfo.add_text("Credit", metadata.get('iptc_credit', 'GroundSwell'))
    pnginfo.add_text("Source", metadata.get('xmp_source', 'GroundSwell'))
    pnginfo.add_text("Creation Time", metadata.get('exif_create_date', ''))

    xmp_data = create_xmp_packet(metadata)
    pnginfo.add_text("XML:com.adobe.xmp", xmp_data)

    output = BytesIO()
    img.save(output, 'PNG', pnginfo=pnginfo)
    return output.getvalue()


def process_image_metadata(image_data: bytes, filename: str, metadata: dict) -> bytes:
    """Process image and add metadata based on file type."""
    ext = Path(filename).suffix.lower()

    if ext in ['.jpg', '.jpeg']:
        return process_jpeg_metadata(image_data, metadata)
    elif ext == '.png':
        return process_png_metadata(image_data, metadata)
    else:
        return image_data


# HTML Template embedded
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GroundSwell Image Metadata Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; }
        .container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
        header { text-align: center; margin-bottom: 40px; }
        .logo { font-size: 2.5rem; font-weight: 700; background: linear-gradient(90deg, #00d4ff, #7c3aed); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #94a3b8; margin-top: 8px; }
        .upload-section { background: rgba(255,255,255,0.05); border: 2px dashed rgba(255,255,255,0.2); border-radius: 16px; padding: 60px 40px; text-align: center; cursor: pointer; transition: all 0.3s; }
        .upload-section:hover { border-color: #00d4ff; background: rgba(0,212,255,0.05); }
        .upload-icon { font-size: 4rem; margin-bottom: 20px; }
        #fileInput { display: none; }
        .processing { display: none; text-align: center; padding: 40px; }
        .spinner { width: 60px; height: 60px; border: 4px solid rgba(255,255,255,0.1); border-left-color: #00d4ff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .results { display: none; margin-top: 40px; }
        .result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .result-title { font-size: 1.8rem; color: #00d4ff; }
        .btn { color: #fff; border: none; padding: 12px 24px; border-radius: 8px; font-size: 1rem; cursor: pointer; transition: all 0.2s; }
        .btn-primary { background: linear-gradient(90deg, #00d4ff, #7c3aed); }
        .btn-secondary { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,212,255,0.3); }
        .metadata-tabs { display: flex; gap: 4px; margin-bottom: 20px; background: rgba(0,0,0,0.2); padding: 4px; border-radius: 12px; }
        .tab-btn { flex: 1; padding: 12px 20px; background: transparent; border: none; color: #94a3b8; cursor: pointer; border-radius: 8px; transition: all 0.3s; }
        .tab-btn.active { background: rgba(124,58,237,0.3); color: #fff; }
        .metadata-panel { display: none; background: rgba(255,255,255,0.05); border-radius: 16px; padding: 30px; }
        .metadata-panel.active { display: block; }
        .metadata-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
        .metadata-field { background: rgba(0,0,0,0.2); border-radius: 10px; padding: 16px; }
        .metadata-field.full-width { grid-column: 1 / -1; }
        .field-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; margin-bottom: 8px; display: flex; justify-content: space-between; }
        .field-tag { font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; }
        .tag-exif { background: rgba(239,68,68,0.2); color: #fca5a5; }
        .tag-iptc { background: rgba(34,197,94,0.2); color: #86efac; }
        .tag-xmp { background: rgba(59,130,246,0.2); color: #93c5fd; }
        .field-input { width: 100%; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 10px 12px; color: #e2e8f0; font-size: 0.95rem; }
        .field-input:focus { outline: none; border-color: #7c3aed; }
        textarea.field-input { min-height: 80px; resize: vertical; }
        .status-message { padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; display: none; }
        .status-message.success { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); color: #86efac; display: block; }
        .status-message.error { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #fca5a5; display: block; }
        .new-upload-btn { display: block; width: 100%; padding: 16px; background: transparent; border: 2px solid rgba(255,255,255,0.2); color: #94a3b8; border-radius: 8px; cursor: pointer; margin-top: 20px; }
        .new-upload-btn:hover { border-color: #00d4ff; color: #00d4ff; }
        footer { text-align: center; margin-top: 60px; color: #64748b; }
        footer a { color: #00d4ff; text-decoration: none; }
        .saving-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: none; justify-content: center; align-items: center; z-index: 1000; }
        .saving-overlay.active { display: flex; }
        .button-group { display: flex; gap: 12px; }
        .panel-header { margin-bottom: 20px; }
        .panel-header h3 { color: #7c3aed; font-size: 1.1rem; margin-bottom: 4px; }
        .panel-header p { color: #64748b; font-size: 0.85rem; }
        .tab-badge { display: inline-block; background: rgba(0,212,255,0.2); color: #00d4ff; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; margin-left: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">GroundSwell℠</div>
            <p class="subtitle">AI-Powered Image Metadata Tool</p>
        </header>

        <div class="upload-section" id="uploadSection">
            <div class="upload-icon">📷</div>
            <p>Drag & drop your image here or <span style="color:#00d4ff">browse files</span></p>
            <p style="color:#64748b;margin-top:10px;font-size:0.9rem">Supports JPG, PNG</p>
            <input type="file" id="fileInput" accept="image/*">
        </div>

        <div class="processing" id="processing">
            <div class="spinner"></div>
            <p>Analyzing image with AI...</p>
        </div>

        <div class="results" id="results">
            <div class="result-header">
                <h2 class="result-title" id="resultTitle">Image Metadata</h2>
                <div class="button-group">
                    <button class="btn btn-secondary" id="resetBtn">Reset to AI Generated</button>
                    <button class="btn btn-primary" id="saveDownloadBtn">Save & Download</button>
                </div>
            </div>

            <div id="statusMessage" class="status-message"></div>

            <div class="metadata-tabs">
                <button class="tab-btn active" data-tab="exif">EXIF <span class="tab-badge">5</span></button>
                <button class="tab-btn" data-tab="iptc">IPTC <span class="tab-badge">9</span></button>
                <button class="tab-btn" data-tab="xmp">XMP <span class="tab-badge">14</span></button>
            </div>

            <div class="metadata-panel active" id="panel-exif">
                <div class="panel-header"><h3>EXIF - Exchangeable Image File Format</h3><p>Standard metadata embedded in image files</p></div>
                <div class="metadata-grid">
                    <div class="metadata-field"><div class="field-label">Create Date <span class="field-tag tag-exif">EXIF</span></div><input type="date" class="field-input" id="exif_create_date"></div>
                    <div class="metadata-field"><div class="field-label">Artist <span class="field-tag tag-exif">EXIF</span></div><input type="text" class="field-input" id="exif_artist" value="GroundSwell"></div>
                    <div class="metadata-field"><div class="field-label">Copyright <span class="field-tag tag-exif">EXIF</span></div><input type="text" class="field-input" id="exif_copyright"></div>
                    <div class="metadata-field full-width"><div class="field-label">Image Description <span class="field-tag tag-exif">EXIF</span></div><textarea class="field-input" id="exif_description"></textarea></div>
                    <div class="metadata-field full-width"><div class="field-label">User Comment (Keywords) <span class="field-tag tag-exif">EXIF</span></div><textarea class="field-input" id="exif_user_comment"></textarea></div>
                </div>
            </div>

            <div class="metadata-panel" id="panel-iptc">
                <div class="panel-header"><h3>IPTC - International Press Telecommunications Council</h3><p>Industry standard for news and media metadata</p></div>
                <div class="metadata-grid">
                    <div class="metadata-field"><div class="field-label">Object Name/Title <span class="field-tag tag-iptc">IPTC</span></div><input type="text" class="field-input" id="iptc_object_name"></div>
                    <div class="metadata-field"><div class="field-label">Headline <span class="field-tag tag-iptc">IPTC</span></div><input type="text" class="field-input" id="iptc_headline"></div>
                    <div class="metadata-field full-width"><div class="field-label">Caption/Abstract <span class="field-tag tag-iptc">IPTC</span></div><textarea class="field-input" id="iptc_caption"></textarea></div>
                    <div class="metadata-field full-width"><div class="field-label">Keywords <span class="field-tag tag-iptc">IPTC</span></div><textarea class="field-input" id="iptc_keywords"></textarea></div>
                    <div class="metadata-field"><div class="field-label">Date Created <span class="field-tag tag-iptc">IPTC</span></div><input type="date" class="field-input" id="iptc_date_created"></div>
                    <div class="metadata-field"><div class="field-label">By-line (Creator) <span class="field-tag tag-iptc">IPTC</span></div><input type="text" class="field-input" id="iptc_byline" value="GroundSwell"></div>
                    <div class="metadata-field"><div class="field-label">Credit <span class="field-tag tag-iptc">IPTC</span></div><input type="text" class="field-input" id="iptc_credit" value="GroundSwell"></div>
                    <div class="metadata-field"><div class="field-label">Copyright Notice <span class="field-tag tag-iptc">IPTC</span></div><input type="text" class="field-input" id="iptc_copyright_notice"></div>
                    <div class="metadata-field"><div class="field-label">Contact <span class="field-tag tag-iptc">IPTC</span></div><input type="text" class="field-input" id="iptc_contact" value="groundswell.co"></div>
                </div>
            </div>

            <div class="metadata-panel" id="panel-xmp">
                <div class="panel-header"><h3>XMP - Extensible Metadata Platform</h3><p>Adobe's standard for metadata in digital files</p></div>
                <div class="metadata-grid">
                    <div class="metadata-field"><div class="field-label">Title <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_title"></div>
                    <div class="metadata-field"><div class="field-label">Label <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_label"></div>
                    <div class="metadata-field"><div class="field-label">Headline <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_headline"></div>
                    <div class="metadata-field full-width"><div class="field-label">Description <span class="field-tag tag-xmp">XMP</span></div><textarea class="field-input" id="xmp_description"></textarea></div>
                    <div class="metadata-field full-width"><div class="field-label">Subject (Keywords) <span class="field-tag tag-xmp">XMP</span></div><textarea class="field-input" id="xmp_subject"></textarea></div>
                    <div class="metadata-field"><div class="field-label">Date Created <span class="field-tag tag-xmp">XMP</span></div><input type="date" class="field-input" id="xmp_date_created"></div>
                    <div class="metadata-field"><div class="field-label">Creator <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_creator" value="GroundSwell"></div>
                    <div class="metadata-field"><div class="field-label">Credit <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_credit" value="GroundSwell"></div>
                    <div class="metadata-field"><div class="field-label">Rights/Copyright <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_rights"></div>
                    <div class="metadata-field"><div class="field-label">Copyright Status <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_copyright_status" value="Protected"></div>
                    <div class="metadata-field"><div class="field-label">Source <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_source" value="GroundSwell"></div>
                    <div class="metadata-field"><div class="field-label">Category <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_category" value="Business Ownership Platform"></div>
                    <div class="metadata-field"><div class="field-label">Website <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_website" value="www.groundswell.co"></div>
                    <div class="metadata-field"><div class="field-label">Phone <span class="field-tag tag-xmp">XMP</span></div><input type="text" class="field-input" id="xmp_phone" value="435-214-2997"></div>
                </div>
            </div>

            <button class="new-upload-btn" id="newUploadBtn">Upload Another Image</button>
        </div>

        <footer><p>Powered by Claude AI | © <span id="year"></span> <a href="https://groundswell.co">GroundSwell℠</a></p></footer>
    </div>

    <div class="saving-overlay" id="savingOverlay"><div><div class="spinner"></div><p>Saving metadata...</p></div></div>

    <script>
        document.getElementById('year').textContent = new Date().getFullYear();
        const uploadSection = document.getElementById('uploadSection');
        const fileInput = document.getElementById('fileInput');
        const processing = document.getElementById('processing');
        const results = document.getElementById('results');
        const statusMessage = document.getElementById('statusMessage');
        const savingOverlay = document.getElementById('savingOverlay');

        let currentFileId = null;
        let originalMetadata = null;

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.metadata-panel').forEach(p => p.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
            });
        });

        uploadSection.addEventListener('click', () => fileInput.click());
        uploadSection.addEventListener('dragover', e => { e.preventDefault(); uploadSection.style.borderColor = '#00d4ff'; });
        uploadSection.addEventListener('dragleave', () => { uploadSection.style.borderColor = 'rgba(255,255,255,0.2)'; });
        uploadSection.addEventListener('drop', e => { e.preventDefault(); uploadSection.style.borderColor = 'rgba(255,255,255,0.2)'; if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]); });
        fileInput.addEventListener('change', e => { if (e.target.files.length) handleFile(e.target.files[0]); });

        document.getElementById('newUploadBtn').addEventListener('click', () => {
            results.style.display = 'none'; uploadSection.style.display = 'block'; fileInput.value = ''; currentFileId = null; originalMetadata = null; statusMessage.className = 'status-message';
        });

        document.getElementById('resetBtn').addEventListener('click', () => { if (originalMetadata) { populateFields(originalMetadata); showStatus('Fields reset to AI-generated values', 'success'); } });

        document.getElementById('saveDownloadBtn').addEventListener('click', async () => {
            if (!currentFileId) return;
            savingOverlay.classList.add('active');
            try {
                const response = await fetch('/save-metadata', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ file_id: currentFileId, metadata: gatherMetadata() })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Save failed');

                // Download the file
                const link = document.createElement('a');
                link.href = 'data:application/octet-stream;base64,' + data.image_data;
                link.download = data.filename;
                link.click();
                showStatus('Metadata saved! Download started.', 'success');
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            } finally {
                savingOverlay.classList.remove('active');
            }
        });

        async function handleFile(file) {
            if (!file.type.startsWith('image/')) { alert('Please upload an image file'); return; }
            uploadSection.style.display = 'none'; processing.style.display = 'block'; results.style.display = 'none';

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/upload', { method: 'POST', body: formData });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Upload failed');

                currentFileId = data.file_id;
                originalMetadata = data.metadata;
                document.getElementById('resultTitle').textContent = data.metadata.title || 'Image Metadata';
                populateFields(data.metadata);
                results.style.display = 'block';
            } catch (error) {
                alert('Error: ' + error.message);
                uploadSection.style.display = 'block';
            } finally {
                processing.style.display = 'none';
            }
        }

        function populateFields(meta) {
            const year = (meta.create_date || new Date().toISOString().split('T')[0]).substring(0, 4);
            const dateValue = meta.create_date || new Date().toISOString().split('T')[0];
            const keywords = Array.isArray(meta.keywords) ? meta.keywords.join(', ') : (meta.keywords || '');

            document.getElementById('exif_create_date').value = dateValue;
            document.getElementById('exif_artist').value = meta.artist || 'GroundSwell';
            document.getElementById('exif_copyright').value = meta.copyright || 'Copyright ' + year + ' GroundSwell';
            document.getElementById('exif_description').value = meta.description || '';
            document.getElementById('exif_user_comment').value = keywords;

            document.getElementById('iptc_object_name').value = meta.title || '';
            document.getElementById('iptc_headline').value = meta.headline || '';
            document.getElementById('iptc_caption').value = meta.description || '';
            document.getElementById('iptc_keywords').value = keywords;
            document.getElementById('iptc_date_created').value = dateValue;
            document.getElementById('iptc_byline').value = meta.artist || 'GroundSwell';
            document.getElementById('iptc_credit').value = meta.credit || 'GroundSwell';
            document.getElementById('iptc_copyright_notice').value = meta.copyright || 'Copyright ' + year + ' GroundSwell';
            document.getElementById('iptc_contact').value = meta.contact || 'groundswell.co';

            document.getElementById('xmp_title').value = meta.title || '';
            document.getElementById('xmp_label').value = meta.title || '';
            document.getElementById('xmp_headline').value = meta.headline || '';
            document.getElementById('xmp_description').value = meta.description || '';
            document.getElementById('xmp_subject').value = keywords;
            document.getElementById('xmp_date_created').value = dateValue;
            document.getElementById('xmp_creator').value = meta.artist || 'GroundSwell';
            document.getElementById('xmp_credit').value = meta.credit || 'GroundSwell';
            document.getElementById('xmp_rights').value = meta.copyright || 'Copyright ' + year + ' GroundSwell';
            document.getElementById('xmp_copyright_status').value = 'Protected';
            document.getElementById('xmp_source').value = 'GroundSwell';
            document.getElementById('xmp_category').value = meta.category || 'Business Ownership Platform';
            document.getElementById('xmp_website').value = meta.website || 'www.groundswell.co';
            document.getElementById('xmp_phone').value = meta.phone || '435-214-2997';
        }

        function gatherMetadata() {
            return {
                exif_create_date: document.getElementById('exif_create_date').value,
                exif_artist: document.getElementById('exif_artist').value,
                exif_copyright: document.getElementById('exif_copyright').value,
                exif_description: document.getElementById('exif_description').value,
                exif_user_comment: document.getElementById('exif_user_comment').value,
                iptc_object_name: document.getElementById('iptc_object_name').value,
                iptc_headline: document.getElementById('iptc_headline').value,
                iptc_caption: document.getElementById('iptc_caption').value,
                iptc_keywords: document.getElementById('iptc_keywords').value,
                iptc_date_created: document.getElementById('iptc_date_created').value,
                iptc_byline: document.getElementById('iptc_byline').value,
                iptc_credit: document.getElementById('iptc_credit').value,
                iptc_copyright_notice: document.getElementById('iptc_copyright_notice').value,
                iptc_contact: document.getElementById('iptc_contact').value,
                xmp_title: document.getElementById('xmp_title').value,
                xmp_label: document.getElementById('xmp_label').value,
                xmp_headline: document.getElementById('xmp_headline').value,
                xmp_description: document.getElementById('xmp_description').value,
                xmp_subject: document.getElementById('xmp_subject').value,
                xmp_date_created: document.getElementById('xmp_date_created').value,
                xmp_creator: document.getElementById('xmp_creator').value,
                xmp_credit: document.getElementById('xmp_credit').value,
                xmp_rights: document.getElementById('xmp_rights').value,
                xmp_copyright_status: document.getElementById('xmp_copyright_status').value,
                xmp_source: document.getElementById('xmp_source').value,
                xmp_category: document.getElementById('xmp_category').value,
                xmp_website: document.getElementById('xmp_website').value,
                xmp_phone: document.getElementById('xmp_phone').value
            };
        }

        function showStatus(message, type) { statusMessage.textContent = message; statusMessage.className = 'status-message ' + type; }
    </script>
</body>
</html>'''


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_TEMPLATE


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """Upload and analyze image with AI."""

    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_id = str(uuid.uuid4())[:8]
    original_filename = file.filename or "image.jpg"

    content = await file.read()

    # Store in memory
    file_storage[file_id] = {
        "data": content,
        "filename": original_filename
    }

    try:
        metadata = await analyze_image_with_claude(content, original_filename)
        year = metadata.get("create_date", datetime.now().strftime("%Y-%m-%d"))[:4]

        return JSONResponse({
            "success": True,
            "file_id": file_id,
            "metadata": {
                "title": metadata.get("title", ""),
                "headline": metadata.get("headline", ""),
                "description": metadata.get("description", ""),
                "keywords": metadata.get("keywords", []),
                "category": metadata.get("category", "Business Ownership Platform"),
                "supplemental_category": metadata.get("supplemental_category", ""),
                "create_date": metadata.get("create_date", datetime.now().strftime("%Y-%m-%d")),
                "artist": "GroundSwell",
                "copyright": f"Copyright {year} GroundSwell",
                "credit": "GroundSwell",
                "contact": "groundswell.co",
                "website": "www.groundswell.co",
                "phone": "435-214-2997"
            }
        })

    except Exception as e:
        if file_id in file_storage:
            del file_storage[file_id]
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.post("/save-metadata")
async def save_metadata(request: SaveMetadataRequest):
    """Save metadata to image and return as base64."""

    file_id = request.file_id
    metadata = request.metadata

    if file_id not in file_storage:
        raise HTTPException(status_code=404, detail="File not found. Please upload again.")

    stored = file_storage[file_id]
    image_data = stored["data"]
    filename = stored["filename"]

    try:
        processed_data = process_image_metadata(image_data, filename, metadata)

        title = metadata.get('xmp_title', metadata.get('iptc_object_name', 'image'))
        safe_title = "".join(c if c.isalnum() or c in ' -_' else '' for c in title).replace(' ', '_')[:50]
        ext = Path(filename).suffix
        output_filename = f"{safe_title}_groundswell{ext}"

        return JSONResponse({
            "success": True,
            "filename": output_filename,
            "image_data": base64.b64encode(processed_data).decode('utf-8')
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving metadata: {str(e)}")
