"""Prompt templates for AI-based scene analysis."""

# Studio detection prompt
STUDIO_DETECTION_PROMPT = """
Analyze the following adult content scene information and identify the production studio.

File path: {file_path}
Title: {title}
Details: {details}
Current studio: {studio}

Available Studios:
{available_studios}

Based on the file path, title, and scene details, determine:
1. The studio name (the PRODUCTION COMPANY that created this content)

IMPORTANT: You MUST only select a studio from the "Available Studios" list above.
If you cannot confidently match to any studio in the list, return "Unknown".

Consider common studio naming patterns in file paths and titles.
Match variations like abbreviations, domains, or partial names to the full studio names in the list.

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
Details: {details}
Current performers: {performers}

Available Performers:
{available_performers}

Identify all performers (actors/models) in this scene. Look for:
1. Names in the file path (often separated by dashes, underscores, or "and")
2. Names mentioned in the title
3. Names in the description/details

IMPORTANT: Match detected names against the "Available Performers" list above.
The list includes performer names and their aliases in the format: "Name (aliases: alias1, alias2)".
Match any variation, nickname, or alias to the official performer name.

Consider these patterns:
- "PerformerA and PerformerB" or "PerformerA & PerformerB"
- "PerformerA_PerformerB" or "PerformerA-PerformerB"
- Partial names, nicknames, or stage name variations

Return a JSON list of performers with confidence scores:
{{
  "performers": [
    {{"name": "Performer Name 1", "confidence": 0.95}},
    {{"name": "Performer Name 2", "confidence": 0.85}}
  ]
}}

Note: Use the official performer name from the list, not the detected variation.
"""

# Tag suggestion prompt
TAG_SUGGESTION_PROMPT = """
Suggest relevant tags for this adult content scene.

File path: {file_path}
Title: {title}
Details: {details}
Current studio: {studio}
Current tags: {tags}
Duration: {duration} seconds
Resolution: {resolution}

Available Tags:
{available_tags}

Suggest appropriate content tags based on:
1. Technical aspects (resolution, duration)
2. Content type inferred from title/path/details
3. Studio style and typical content
4. Scene participants and activities

IMPORTANT: You MUST only suggest tags from the "Available Tags" list above.
Do NOT create new tags or suggest tags not in the list.

Avoid:
- Tags already present in "Current tags"
- Tags that don't match the scene content
- Generic tags when more specific ones apply

Return a JSON list of suggested tags with confidence:
{{
  "tags": [
    {{"name": "tag1", "confidence": 0.9}},
    {{"name": "tag2", "confidence": 0.85}}
  ]
}}
"""
