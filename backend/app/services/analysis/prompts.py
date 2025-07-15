"""Prompt templates for AI-based scene analysis."""

# Studio detection prompt
STUDIO_DETECTION_PROMPT = """
Analyze the following adult content scene information and identify the production studio.

File path: {file_path}
Title: {title}
Current studio: {studio}

Based on the file path and title, determine:
1. The studio name (the PRODUCTION COMPANY that created this content)

Consider common studio naming patterns in file paths and titles. Studios are companies like:
- Major studios: Sean Cody, Lucas Entertainment, Raw Fuck Club, Men.com, etc.
- Independent studios: OnlyFans creators, amateur producers, etc.

Return ONLY the studio name if found, or "Unknown" if not identifiable.
Confidence should be between 0 and 1.

Format your response as JSON:
{{
  "studio": "Studio Name",
  "confidence": 0.9
}}
"""

# Performer detection prompt
PERFORMER_DETECTION_PROMPT = """
Extract performer names from the following adult content scene information.

File path: {file_path}
Title: {title}
Current performers: {performers}
Details: {details}

Identify all performers (actors/models) in this scene. Look for:
1. Names in the file path (often separated by dashes, underscores, or "and")
2. Names mentioned in the title
3. Names in the description/details

Consider these patterns:
- "PerformerA and PerformerB" or "PerformerA & PerformerB"
- "PerformerA_PerformerB" or "PerformerA-PerformerB"
- Stage names vs real names (prefer stage names)

Return a JSON list of performers with confidence scores:
{{
  "performers": [
    {{"name": "Performer Name 1", "confidence": 0.95}},
    {{"name": "Performer Name 2", "confidence": 0.85}}
  ]
}}
"""

# Tag suggestion prompt
TAG_SUGGESTION_PROMPT = """
Suggest relevant tags for this adult content scene.

File path: {file_path}
Title: {title}
Details: {details}
Current tags: {tags}
Duration: {duration} seconds
Resolution: {resolution}

Suggest appropriate content tags based on:
1. Technical aspects (resolution, duration)
2. Content type inferred from title/path
3. Studio style (if identifiable)
4. Common adult content categories

Avoid:
- Redundant tags already present
- Overly specific tags
- Inappropriate or offensive tags

Return a JSON list of suggested tags with confidence:
{{
  "tags": [
    {{"name": "tag1", "confidence": 0.9}},
    {{"name": "tag2", "confidence": 0.85}}
  ]
}}
"""

# Description generation prompt
DESCRIPTION_GENERATION_PROMPT = """
Generate a concise, professional description for this adult content scene.

File path: {file_path}
Title: {title}
Studio: {studio}
Performers: {performers}
Duration: {duration} seconds
Resolution: {resolution}
Current description: {details}

Create a brief (2-3 sentence) description that:
1. Summarizes the scene content professionally
2. Mentions key performers if known
3. Includes relevant production details
4. Maintains appropriate tone for adult content metadata

If a description exists, enhance it rather than replacing completely.

Return JSON with the description and confidence:
{{
  "description": "Your generated description here",
  "confidence": 0.9
}}
"""

# Batch analysis prompt template
BATCH_ANALYSIS_PROMPT = """
Analyze multiple adult content scenes for metadata detection.

For each scene below, identify:
1. Studio (production company)
2. Performers (actors/models)
3. Suggested tags
4. Brief description

Return results as a JSON object with scene IDs as keys.

Scenes to analyze:
{scenes_list}

Format:
{{
  "scene_id_1": {{
    "studio": {{"name": "Studio Name", "confidence": 0.9}},
    "performers": [{{"name": "Name", "confidence": 0.9}}],
    "tags": [{{"name": "tag", "confidence": 0.8}}],
    "description": {{"text": "Description", "confidence": 0.85}}
  }},
  "scene_id_2": {{ ... }}
}}
"""

# Performer alias matching prompt
PERFORMER_ALIAS_PROMPT = """
Match the following detected performer name with known performers and their aliases.

Detected name: {detected_name}
Known performers and aliases:
{performer_list}

Find the best match considering:
1. Exact matches (case-insensitive)
2. Partial matches (first/last name)
3. Common misspellings or variations
4. Nickname to full name mappings

Return JSON with the match:
{{
  "matched_performer": "Official Performer Name",
  "confidence": 0.95,
  "reason": "Exact alias match"
}}

If no match found, return:
{{
  "matched_performer": null,
  "confidence": 0.0,
  "reason": "No match found"
}}
"""

# Studio pattern matching prompt
STUDIO_PATTERN_PROMPT = """
Identify the studio from this file path using common naming patterns.

File path: {file_path}
Known studio patterns:
{studio_patterns}

Look for:
1. Studio abbreviations or codes
2. Website domains in the path
3. Common folder structures used by studios
4. Release naming conventions

Return the most likely studio:
{{
  "studio": "Studio Name",
  "confidence": 0.9,
  "pattern_matched": "pattern description"
}}
"""
