# Non-AI Analysis Job

## Overview

The Non-AI Analysis job performs scene analysis using only pattern matching and rule-based detection methods, without any AI/LLM calls. This is useful for quick, cost-free analysis of scenes using deterministic logic.

## Job Type

- **Type**: `NON_AI_ANALYSIS`
- **Handler**: `analyze_scenes_non_ai_job` (backend/app/jobs/analysis_jobs.py:123)

## Key Differences from AI Analysis

1. **No OpenAI API calls** - Runs completely offline
2. **Does NOT mark scenes as analyzed** - Allows scenes to be re-analyzed with AI later
3. **Deterministic results** - Same input always produces same output
4. **Faster and free** - No API costs or network latency

## Processing Steps

### 1. Performer Detection

The job detects performers through two main methods:

#### A. Path and Title Detection (`detect_from_path`)

Matches performers by analyzing:

1. **Filename** - Extracts potential names from the video filename
2. **Parent directory** - Checks the parent folder name
3. **Scene title** - If provided, extracts names from the title

The extraction process:

1. **Separator-based extraction** - Splits text using common separators:
   - Word separators: `" and "`, `" & "`, `", "`, `" with "`, `" feat "`, `" ft "`, `" featuring "`
   - Symbol separators: `" - "`, `"_"`

2. **Word extraction** - Individual words that could be single-word performer names

3. **Name cleaning** - Removes common non-name words:
   - Technical terms: `scene`, `part`, `episode`, `video`, `clip`
   - Quality indicators: `hd`, `1080p`, `720p`, `4k`, `uhd`
   - File extensions: `mp4`, `avi`, `mkv`, `wmv`, `mov`
   - Adult content terms: Various explicit terms

4. **Matching against known performers**:
   - **Exact match** (confidence: 1.0) - Name matches performer name exactly
   - **Alias match** (confidence: 0.95) - Name matches a performer alias
   - **Partial match** (confidence: 0.6-0.9) - Based on similarity scoring:
     - Substring matching (0.8 if one contains the other)
     - First name match (0.7)
     - Last name match (0.75)
     - String similarity ratio (using SequenceMatcher)
   - **Unmatched names** (confidence: 0.5) - Valid names not in database

#### B. OFScraper Path Detection (`detect_from_ofscraper_path`)

Specifically detects performers from OFScraper directory structure:

**Expected path format**: `/data/ofscraper/{performer_name}/Posts/Videos/file.mp4`

The detection process:

1. **Path validation** - Checks for:
   - Presence of "ofscraper" in path
   - "data" directory before "ofscraper"
   - Directory after "ofscraper" (the performer name)

2. **Performer matching**:
   - **Alias match** (confidence: 0.95) - Extracted name matches performer alias
   - **Name match** (confidence: 0.9) - Extracted name matches performer name
   - **New performer** (confidence: 0.85) - Name not found, create new

### 2. HTML Cleaning from Details

The job cleans HTML tags and entities from scene details/descriptions:

1. **HTML tag removal** - Uses HTMLParser to strip all HTML tags
2. **Entity decoding** - Converts HTML entities:
   - `&amp;` → `&`
   - `&lt;` → `<`
   - `&gt;` → `>`
   - `&quot;` → `"`
   - `&#39;` → `'`
   - `&nbsp;` → ` ` (space)
3. **Whitespace normalization** - Collapses multiple spaces/newlines
4. **Length truncation** - Limits to 500 characters at sentence boundaries

## Field Matching Details

### Performer Detection Fields

The following fields are examined for performer detection:

1. **file_path** (Scene.path) - The full file path
   - Filename (without extension)
   - Parent directory name
   - OFScraper path structure

2. **title** (Scene.title) - The scene title if present

3. **performers** (Scene.performers) - Existing performers (to avoid duplicates)

### Details Cleaning Fields

1. **details** (Scene.details) - The scene description/details field

## Confidence Thresholds

The default confidence threshold is **0.6** (60%). Only detection results meeting or exceeding this threshold are included in the proposed changes.

Confidence levels by detection type:
- Exact name match: **100%**
- Alias match: **95%**
- OFScraper path (matched): **90-95%**
- OFScraper path (new): **85%**
- Partial name match: **60-90%**
- Unmatched valid names: **50%** (below default threshold)

## Output

The job creates an AnalysisPlan with proposed changes:

- **Performer additions** - New performers to add to scenes
- **Details updates** - Cleaned HTML-free descriptions

The plan status is set to DRAFT and can be reviewed/applied later.

## Use Cases

1. **Quick initial analysis** - Fast first pass before expensive AI analysis
2. **Bulk import processing** - Handle OFScraper imports without API costs
3. **HTML cleanup** - Fix descriptions with HTML tags
4. **Path-based organization** - Detect performers from well-organized file structures

## Technical Implementation

- Main entry point: `analyze_scenes_non_ai_job()` (backend/app/jobs/analysis_jobs.py:123)
- Analysis service: `analyze_scenes_non_ai()` (backend/app/services/analysis/analysis_service.py:178)
- Performer detector: `PerformerDetector` class (backend/app/services/analysis/performer_detector.py:16)
- Details generator: `DetailsGenerator` class (backend/app/services/analysis/details_generator.py:30)