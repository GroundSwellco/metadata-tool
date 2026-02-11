# GroundSwell℠ Image Metadata Tool

AI-powered tool that automatically generates and embeds EXIF, IPTC, and XMP metadata for GroundSwell℠ images using Claude's vision capabilities.

## Features

- **AI-Powered Analysis**: Uses Claude to analyze images and generate appropriate metadata
- **Complete Metadata Support**: Writes EXIF, IPTC, and XMP metadata fields
- **GroundSwell℠ Branding**: Automatically applies GroundSwell branding, contact info, and copyright
- **Web Interface**: Simple drag-and-drop interface for uploading images
- **Download Ready**: Get your images back with all metadata embedded

## Setup

### 1. Install Python Dependencies

```bash
cd groundswell-metadata-tool
pip install -r requirements.txt
```

### 2. Install ExifTool

ExifTool is required to write metadata to images.

**Windows:**
1. Download from: https://exiftool.org/
2. Extract `exiftool(-k).exe` and rename to `exiftool.exe`
3. Move to `C:\Windows\` or add to your PATH

**Or using Chocolatey:**
```bash
choco install exiftool
```

### 3. Configure API Key

Create a `.env` file in the project folder:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

You can get an API key from: https://console.anthropic.com/

### 4. Run the Application

```bash
python app.py
```

Or double-click `run.bat`

Open your browser to: http://localhost:8000

## Usage

1. Open the web interface at http://localhost:8000
2. Drag and drop an image or click to browse
3. Wait for AI analysis (uses Claude's vision to understand the image)
4. Review the generated metadata
5. Download your image with embedded metadata

## Metadata Fields

### EXIF
- Artist (GroundSwell)
- Copyright
- Image Description
- User Comment (keywords)

### IPTC
- Object Name/Title
- Headline
- Caption Abstract
- Keywords
- Credit, Copyright Notice
- By-line, Contact

### XMP
- Label, Title
- Headline, Description
- Subject (keywords)
- Creator, Credit, Rights
- Source, Category
- Supplemental Categories

## Contact

- Website: www.groundswell.co
- Phone: 435-214-2997
