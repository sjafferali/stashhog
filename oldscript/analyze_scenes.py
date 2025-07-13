#!/usr/bin/env python3
"""
Stash Scene Analyzer with Plan Generation Support

This script can analyze scenes and either apply changes immediately or generate
a plan file for review before applying changes.

Plan File Structure (JSON):
{
  "metadata": {
    "generated_at": "2024-01-15T10:30:00Z",
    "script_version": "1.0",
    "settings": {
      "detect_studios": true,
      "detect_performers": true,
      "detect_tags": true,
      "detect_details": true
    }
  },
  "scenes": [
    {
      "scene_id": 3066,
      "current_state": {
        "title": "Scene Title",
        "path": "/path/to/file.mp4",
        "studio": null,
        "performers": ["Current Performer"],
        "tags": ["Current Tag"],
        "details": "Current description"
      },
      "proposed_changes": {
        "studio": {
          "action": "set",
          "value": "New Studio",
          "confidence": 0.9
        },
        "performers": {
          "action": "add",
          "values": ["New Performer 1", "New Performer 2"]
        },
        "tags": {
          "action": "add",
          "values": ["New Tag 1", "New Tag 2"]
        },
        "details": {
          "action": "update",
          "value": "New AI-generated description"
        }
      }
    }
  ]
}

Usage Examples:
  # Generate a plan file
  python analyze_scenes.py --detect-studios --generate-plan changes.json

  # Review the plan file, then apply it
  python analyze_scenes.py --apply-plan changes.json --apply-changes --create-missing
"""

import argparse
import os
import re
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import dateutil.parser
import dateutil.relativedelta
import openai
from stashapi.stashapp import StashInterface

# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Set up a single logger for the entire application
logger = logging.getLogger('stashscripts')
logger.propagate = False  # Don't propagate to the root logger

# Disable other loggers that might cause duplicate output
logging.getLogger('stashapi').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)

class SceneAnalyzer:
    def __init__(self, stash_url, api_key=None, openai_api_key=None, openai_model=None, openai_base_url=None, use_titles=False, use_details=False, use_studio=False,
                 detect_performers=False, detect_studios=False, detect_tags=False, detect_details=False, split_names=False,
                 apply_changes=False, create_missing=False, mark_tag=None, dry_run=False, log_level=logging.INFO, 
                 show_prompts=False, colorize=False):
        conn = {}
        if stash_url.startswith(('http://', 'https://')):
            # Parse URL if it's a full URL
            import urllib.parse
            parsed_url = urllib.parse.urlparse(stash_url)
            conn = {
                "scheme": parsed_url.scheme,
                "host": parsed_url.hostname,
                "port": str(parsed_url.port) if parsed_url.port else "9999"
            }
        else:
            # Assume it's just the host:port or host
            parts = stash_url.split(':')
            host = parts[0]
            port = parts[1] if len(parts) > 1 else "9999"
            conn = {
                "scheme": "http",
                "host": host,
                "port": port
            }
        
        if api_key:
            conn["ApiKey"] = api_key
        
        # Setup OpenAI client if API key is provided
        self.use_titles = use_titles
        self.use_details = use_details
        self.use_studio = use_studio
        self.detect_performers = detect_performers
        self.detect_studios = detect_studios
        self.detect_tags = detect_tags
        self.detect_details = detect_details
        self.split_names = split_names
        self.apply_changes = apply_changes
        self.create_missing = create_missing
        self.mark_tag = mark_tag
        self.dry_run = dry_run
        self.show_prompts = show_prompts
        self.colorize = colorize
        self.openai_client = None
        # Default to gpt-3.5-turbo-16k if no model is specified
        self.openai_model = openai_model or "gpt-3.5-turbo-16k"
        
        # Determine if we need to use OpenAI for any detections
        needs_openai = detect_performers or detect_studios or detect_tags
        
        # Only initialize OpenAI client if we need it AND not in dry run mode
        self.openai_client = None
        if openai_api_key and not dry_run and needs_openai:
            openai.api_key = openai_api_key
            # Initialize the OpenAI client with optional custom base URL
            client_params = {"api_key": openai_api_key}
            if openai_base_url:
                client_params["base_url"] = openai_base_url
                logger.debug(f"Using custom OpenAI base URL: {openai_base_url}")
            
            self.openai_client = openai.OpenAI(**client_params)
            logger.debug(f"Using OpenAI model: {self.openai_model}")
        elif needs_openai:
            # We need AI but either no key provided or in dry run mode
            logger.debug(f"OpenAI client not initialized (dry run: {dry_run}, API key provided: {bool(openai_api_key)})")
        else:
            # AI detections not enabled
            logger.debug("OpenAI client not initialized (no AI-backed detections enabled)")
            
        self.stash = StashInterface(conn)
        self.studio_patterns = {
            r'(?i)/([^/]+?)/scenes/': 1,  # Typical structure with studio in path
            r'(?i)/studios/([^/]+?)/': 1,  # Explicit studios directory
            r'(?i)/(?:videos|movies)/([^/]+?)/': 1,  # Common alternative folders
        }
        self.performer_patterns = {
            r'(?i)/performers/([^/]+?)/': 1,  # Explicit performers directory
            r'(?i)/([^/]+?)(?:\s*[&+]\s*([^/]+?))?/scenes/': [1, 2],  # Studio/performer naming convention
            r'(?i)_([^_]+?)(?:\s*[&+]\s*([^_]+?))?_': [1, 2],  # Performer in filename with underscore separation
        }
        
    def _parse_date_filter(self, date_str):
        "Parse date filters with support for relative dates."
        if not date_str:
            return None
            
        try:
            # Check for relative date specification
            if 'ago' in date_str.lower():
                # Parse patterns like "5 days ago", "1 month ago", etc.
                pattern = r'(\d+)\s+(day|days|week|weeks|month|months|year|years)\s+ago'
                match = re.match(pattern, date_str.lower())
                
                if match:
                    num = int(match.group(1))
                    unit = match.group(2)
                    
                    today = datetime.datetime.now()
                    if unit in ['day', 'days']:
                        return today - dateutil.relativedelta.relativedelta(days=num)
                    elif unit in ['week', 'weeks']:
                        return today - dateutil.relativedelta.relativedelta(weeks=num)
                    elif unit in ['month', 'months']:
                        return today - dateutil.relativedelta.relativedelta(months=num)
                    elif unit in ['year', 'years']:
                        return today - dateutil.relativedelta.relativedelta(years=num)
            
            # Try to parse as a standard date
            return dateutil.parser.parse(date_str)
        except (ValueError, TypeError):
            logger.error(f"Could not parse date filter: {date_str}")
            return None

    def analyze_scenes(self, verbose=False, batch_size=15, limit=None, scene_id=None, 
                       include_tags=None, exclude_tags=None, include_performers=None, 
                       title_filter=None, organized=None, path_filter=None,
                       created_after=None, created_before=None, date_after=None, date_before=None):
        "Analyzes scenes in Stash and prints differences between detected and assigned metadata."
        # Note: The logger is now configured in main() only, not here
        # This prevents multiple handlers being added
            
        logger.debug("Starting scene analysis")
        
        # If a specific scene_id is provided, only analyze that scene
        if scene_id:
            query = (
                "query FindScene($id: ID!) {"
                "  findScene(id: $id) {"
                "    id"
                "    title"
                "    details"
                "    files {"
                "      path"
                "    }"
                "    studio {"
                "      name"
                "    }"
                "    performers {"
                "      name"
                "    }"
                "  }"
                "}"
            )
            logger.debug(f"Fetching scene with ID {scene_id}")
            result = self.stash.call_GQL(query, {'id': scene_id})
            scene = result.get('findScene')
            
            if not scene:
                logger.error(f"Scene with ID {scene_id} not found")
                return
                
            scenes = [scene]
            logger.info(f"Analyzing only scene ID {scene_id}: {scene.get('title', 'Untitled')}")
        else:
            # Get all scenes with proper pagination
            page = 1
            per_page = 100  # Fetch 100 scenes at a time
            scenes = []
            total_count = 0
            
            logger.debug("Fetching scenes with pagination and filters")
            
            # Build the scene filter based on parameters
            scene_filter = {}
            filter_conditions = []
            
            # Tag filters
            if include_tags:
                include_tag_ids = self._get_tag_ids(include_tags)
                if include_tag_ids:
                    scene_filter['tags'] = {'value': include_tag_ids, 'modifier': 'INCLUDES_ALL'}
                    filter_conditions.append(f"including tags: {', '.join(include_tags)}")
                    
            if exclude_tags:
                exclude_tag_ids = self._get_tag_ids(exclude_tags)
                if exclude_tag_ids:
                    if 'tags' not in scene_filter:
                        scene_filter['tags'] = {}
                    scene_filter['tags']['excludes'] = exclude_tag_ids
                    filter_conditions.append(f"excluding tags: {', '.join(exclude_tags)}")
            
            # Performer filter
            if include_performers:
                performer_ids = self._get_performer_ids(include_performers)
                if performer_ids:
                    scene_filter['performers'] = {'value': performer_ids, 'modifier': 'INCLUDES_ALL'}
                    filter_conditions.append(f"including performers: {', '.join(include_performers)}")
            
            # Title filter
            if title_filter:
                scene_filter['title'] = {'value': title_filter, 'modifier': 'INCLUDES'}
                filter_conditions.append(f"title contains: {title_filter}")
            
            # Path filter
            if path_filter:
                scene_filter['path'] = {'value': path_filter, 'modifier': 'INCLUDES'}
                filter_conditions.append(f"path contains: {path_filter}")
            
            # Organized flag
            if organized is not None:
                scene_filter['organized'] = organized
                filter_conditions.append(f"organized: {'yes' if organized else 'no'}")
            
            # Created date filters
            created_after_date = self._parse_date_filter(created_after)
            created_before_date = self._parse_date_filter(created_before)
            
            if created_after_date:
                scene_filter['created_at'] = {'value': created_after_date.strftime('%Y-%m-%dT%H:%M:%S%z'), 'modifier': 'GREATER_THAN'}
                filter_conditions.append(f"created after: {created_after}")
                
            if created_before_date:
                if 'created_at' not in scene_filter:
                    scene_filter['created_at'] = {}
                scene_filter['created_at']['value2'] = created_before_date.strftime('%Y-%m-%dT%H:%M:%S%z')
                scene_filter['created_at']['modifier'] = 'BETWEEN'
                filter_conditions.append(f"created before: {created_before}")
            
            # Scene date filters
            date_after_date = self._parse_date_filter(date_after)
            date_before_date = self._parse_date_filter(date_before)
            
            if date_after_date:
                scene_filter['date'] = {'value': date_after_date.strftime('%Y-%m-%d'), 'modifier': 'GREATER_THAN'}
                filter_conditions.append(f"date after: {date_after}")
                
            if date_before_date:
                if 'date' not in scene_filter:
                    scene_filter['date'] = {}
                scene_filter['date']['value2'] = date_before_date.strftime('%Y-%m-%d')
                scene_filter['date']['modifier'] = 'BETWEEN'
                filter_conditions.append(f"date before: {date_before}")
            
            if filter_conditions:
                logger.info(f"Applying filters: {', '.join(filter_conditions)}")
            
            while True:
                query = (
                    "query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType) {"
                    "  findScenes(filter: $filter, scene_filter: $scene_filter) {"
                    "    count"
                    "    scenes {"
                    "      id"
                    "      title"
                    "      details"
                    "      files {"
                    "        path"
                    "      }"
                    "      studio {"
                    "        name"
                    "      }"
                    "      performers {"
                    "        name"
                    "      }"
                    "      tags {"
                    "        id"
                    "        name"
                    "      }"
                    "      organized"
                    "      created_at"
                    "      updated_at"
                    "      date"
                    "    }"
                    "  }"
                    "}"
                )
                
                variables = {
                    "filter": {
                        "page": page,
                        "per_page": per_page
                    },
                    "scene_filter": scene_filter if scene_filter else None
                }
                
                result = self.stash.call_GQL(query, variables)
                
                page_scenes = result.get('findScenes', {}).get('scenes', [])
                total_count = result.get('findScenes', {}).get('count', 0)
                
                if page_scenes:
                    scenes.extend(page_scenes)
                    logger.debug(f"Fetched page {page} with {len(page_scenes)} scenes")
                
                if len(page_scenes) < per_page:
                    # This was the last page
                    break
                    
                # Move to the next page
                page += 1
                
            logger.info(f"Found {len(scenes)} scenes (total in Stash: {total_count})")
        
        # Filter scenes with valid files
        valid_scenes = []
        for scene in scenes:
            scene_files = scene.get('files', [])
            if scene_files and scene_files[0].get('path', ''):
                # Add file path to scene object for convenience
                scene['file_path'] = scene_files[0].get('path', '')
                valid_scenes.append(scene)
            elif not scene_files:
                logger.warning(f"Scene {scene.get('id')} '{scene.get('title', 'Untitled')}' has no files")
        
        # Apply limit if specified and not analyzing a specific scene
        if not scene_id and limit and limit > 0:
            # In dry run, show how many scenes would be processed
            if self.dry_run:
                if limit >= len(valid_scenes):
                    logger.info(f"Would analyze all {len(valid_scenes)} scenes")
                else:
                    logger.info(f"Would limit analysis to {limit} scenes (out of {len(valid_scenes)} total)")
            else:
                logger.info(f"Limiting analysis to {limit} scenes (out of {len(valid_scenes)} total)")
            
            valid_scenes = valid_scenes[:limit]
        
        # Determine if we need to use OpenAI for any detections
        needs_openai = self.detect_performers or self.detect_studios or self.detect_tags or self.detect_details
        
        # Process AI detection in batches, but only if needed
        ai_results = {}
        if needs_openai:
            if self.dry_run:
                logger.info("DRY RUN: Would process scenes with AI, but skipping API calls")
                
                # Provide cost estimate in dry run mode
                self._estimate_openai_cost(valid_scenes, batch_size)
                    
            elif self.openai_client and valid_scenes:
                # Provide cost estimate before making actual API calls
                self._estimate_openai_cost(valid_scenes, batch_size)
                
                logger.info(f"Using AI for detection with batch size {batch_size}")
                ai_results = self._batch_detect_with_ai(valid_scenes, batch_size)
        else:
            logger.info("Skipping OpenAI API calls as no AI-backed detections are enabled")
        
        # Get existing entities for comparison, but only if needed
        existing_performers = []
        existing_studios = []
        tag_list = []  # Initialize tag_list here so it's available in scope
        try:
            # Only fetch performers if performer detection is enabled
            if self.detect_performers:
                logger.debug("Fetching all performers for comparison and alias matching")
                existing_performers = self._get_all_performers()
                logger.debug(f"Found {len(existing_performers)} performers")
            
            # Only fetch studios if studio detection is enabled
            if self.detect_studios:
                logger.debug("Fetching all studios for comparison")
                existing_studios = self._get_all_studios()
                logger.debug(f"Found {len(existing_studios)} studios")
            
            # Only fetch tags if tag detection is enabled
            if self.detect_tags:
                logger.debug("Fetching all tags for comparison")
                tag_list = self._get_all_tags()
                logger.debug(f"Found {len(tag_list)} tags")
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for comparison: {e}")
        
        # Process each scene with results
        total_scenes = len(valid_scenes)
        for i, scene in enumerate(valid_scenes, 1):
            scene_path = scene['file_path']
            title = scene.get('title') or os.path.basename(scene_path)
            
            # Add progress indicator for both modes
            progress = f"[{i}/{total_scenes}]"
                
            if self.dry_run:
                logger.info(f"DRY RUN: {progress} Would analyze scene: {title}")
                logger.debug(f"Path: {scene_path}")
                
                # For non-verbose mode in dry run, just print the scene title with progress
                if not verbose:
                    separator = '-' * 50
                    scene_id = scene.get('id')
                    if self.colorize:
                        print(f"\n{Colors.BLUE}{separator}{Colors.RESET}")
                        print(f"{Colors.BOLD}[DRY RUN]{Colors.RESET} Would analyze scene {progress}")
                        print(f"   ID: {scene_id}")
                        print(f"   Title: {title}")
                        print(f"{Colors.BLUE}{separator}{Colors.RESET}")
                    else:
                        print(f"\n{separator}")
                        print(f"[DRY RUN] Would analyze scene {progress}")
                        print(f"   ID: {scene_id}")
                        print(f"   Title: {title}")
                        print(f"{separator}")
                
                # Skip further processing in dry run mode
                continue
            
            logger.info(f"Analyzing scene: {progress} {title}")
            logger.debug(f"Path: {scene_path}")
            
            # For non-verbose mode, still show a basic indicator of progress
            if not verbose:
                separator = '-' * 50
                scene_id = scene.get('id')
                if self.colorize:
                    print(f"\n{Colors.BLUE}{separator}{Colors.RESET}")
                    print(f"{Colors.BOLD}[ANALYZING]{Colors.RESET} Scene: {progress}")
                    print(f"   ID: {scene_id}")
                    print(f"   Title: {title}")
                    print(f"{Colors.BLUE}{separator}{Colors.RESET}")
                else:
                    print(f"\n{separator}")
                    print(f"[ANALYZING] Scene: {progress}")
                    print(f"   ID: {scene_id}")
                    print(f"   Title: {title}")
                    print(f"{separator}")
                # Keep flush=True to ensure immediate output but don't keep the line open
                # We'll use the differences system to show OK or issues
            
            # Get current scene metadata
            current_studio = scene.get('studio', {}).get('name') if scene.get('studio') else None
            current_performers = [p.get('name') for p in scene.get('performers', [])]
            
            # Get AI detection results
            if scene_path in ai_results:
                # Get results based on what detection features are enabled
                detected_studio = ai_results[scene_path].get('studio') if self.detect_studios else None
                detected_performers = ai_results[scene_path].get('performers', []) if self.detect_performers else []
                matched_aliases = ai_results[scene_path].get('matched_aliases', []) if self.detect_performers else []
                
                # Log performer aliases if detected
                if self.detect_performers and matched_aliases:
                    logger.info(f"Matched aliases from database: {', '.join(matched_aliases)}")
                    
                    # Check if the matched aliases correspond to performers that exist in Stash
                    for alias in matched_aliases:
                        # Try to find a performer by alias
                        for performer in existing_performers:
                            if performer.get('name', '').lower() == alias.lower():
                                if performer.get('name') not in current_performers:
                                    logger.info(f"Alias '{alias}' corresponds to existing performer '{performer.get('name')}' not assigned to scene")
            else:
                # No results found
                logger.debug("No AI detection results for this scene")
                detected_studio = None if self.detect_studios else None
                detected_performers = [] if self.detect_performers else []
                matched_aliases = [] if self.detect_performers else []
            
            # Extract potential performer aliases from path
            potential_aliases = self._extract_performer_aliases(scene_path)
            if potential_aliases:
                logger.debug(f"Extracted aliases from path: {', '.join(potential_aliases)}")
            
            # Try to match aliases to existing performers
            if potential_aliases and existing_performers:
                for alias in potential_aliases:
                    logger.debug(f"Checking potential performer alias: {alias}")
                    
                    # Get the cleanly formatted alias
                    clean_alias = self._clean_name(alias)
                    
                    # Only look for exact performer name matches (simplified logic)
                    matched_performer = self._match_alias_to_performer(alias, existing_performers)
                    if matched_performer:
                        logger.info(f"Found performer match for alias '{alias}': {matched_performer}")
                        
                        # Only add if not already in the list
                        if matched_performer not in detected_performers:
                            detected_performers.append(matched_performer)
                    else:
                        logger.debug(f"No performer match found for alias: {alias}")
            
            # Print differences
            has_differences = False
            differences = []
            
            # Track changes that were applied
            applied_changes = []
            
            # Check for studio differences if studio detection is enabled
            if self.detect_studios and detected_studio and detected_studio != current_studio:
                has_differences = True
                
                # Check if the studio exists in Stash
                studio_exists = self._studio_exists_in_stash(detected_studio, existing_studios)
                studio_id = None
                
                if studio_exists:
                    # Get the studio ID
                    studio_id = self._get_studio_id(detected_studio, existing_studios)
                    if self.colorize:
                        message = f"Missing Studio: '{detected_studio}' ({Colors.GREEN}[✓]{Colors.RESET} exists in Stash)"
                    else:
                        message = f"Missing Studio: '{detected_studio}' ([+] exists in Stash)"
                else:
                    if self.create_missing and not self.dry_run:
                        # Create the studio
                        studio_id = self._create_studio(detected_studio)
                        if studio_id:
                            applied_changes.append(f"Created studio: '{detected_studio}'")
                            if self.colorize:
                                message = f"Missing Studio: '{detected_studio}' ({Colors.GREEN}[+]{Colors.RESET} created in Stash)"
                            else:
                                message = f"Missing Studio: '{detected_studio}' ([+] created in Stash)"
                        else:
                            if self.colorize:
                                message = f"Missing Studio: '{detected_studio}' ({Colors.RED}[!]{Colors.RESET} failed to create in Stash)"
                            else:
                                message = f"Missing Studio: '{detected_studio}' ([!] failed to create in Stash)"
                    else:
                        if self.colorize:
                            message = f"Missing Studio: '{detected_studio}' ({Colors.RED}[!]{Colors.RESET} does NOT exist in Stash - needs to be created)"
                        else:
                            message = f"Missing Studio: '{detected_studio}' ([!] does NOT exist in Stash - needs to be created)"
                
                # Apply studio update if necessary
                if self.apply_changes and not self.dry_run and studio_id:
                    # Update the scene with the studio
                    if self._update_scene(scene['id'], {"studio_id": studio_id}):
                        applied_changes.append(f"Applied studio: '{detected_studio}' to scene")
                        if self.colorize:
                            message += f" ({Colors.GREEN}[✓]{Colors.RESET} applied to scene)"
                        else:
                            message += f" ([+] applied to scene)"
                    else:
                        if self.colorize:
                            message += f" ({Colors.RED}[!]{Colors.RESET} failed to apply to scene)"
                        else:
                            message += f" ([!] failed to apply to scene)"
                
                if not current_studio:
                    logger.warning(f"Scene missing studio: '{detected_studio}'")
                else:
                    if self.colorize:
                        message = f"Different Studio: '{Colors.YELLOW}{detected_studio}{Colors.RESET}' vs current '{current_studio}'" + (f" ({Colors.GREEN}[✓]{Colors.RESET} updated)" if self.apply_changes and not self.dry_run and studio_id else "")
                    else:
                        message = f"Different Studio: '{detected_studio}' vs current '{current_studio}'" + (f" ([+] updated)" if self.apply_changes and not self.dry_run and studio_id else "")
                    logger.warning(f"Scene has different studio: '{current_studio}' vs detected '{detected_studio}'")
                
                # Add to differences list for formatted output
                differences.append({"type": "studio", "message": message})
            
            # Check for performer differences if performer detection is enabled
            missing_performers = []
            if self.detect_performers:
                # Track performer IDs to add to the scene
                performer_ids_to_add = []
                
                for performer in detected_performers:
                    if performer and performer not in current_performers:
                        has_differences = True
                        performer_id = None
                        
                        # Check if the performer exists in Stash
                        performer_exists = self._performer_exists_in_stash(performer, existing_performers)
                        
                        if performer_exists:
                            # Get the performer ID
                            performer_id = self._get_performer_id(performer, existing_performers)
                            if self.colorize:
                                message = f"Missing Performer: '{performer}' ({Colors.GREEN}[✓]{Colors.RESET} exists in Stash)"
                            else:
                                message = f"Missing Performer: '{performer}' ([+] exists in Stash)"
                            
                            # Add performer ID to list for scene update
                            if performer_id:
                                performer_ids_to_add.append(performer_id)
                        else:
                            if self.create_missing and not self.dry_run:
                                # Create the performer
                                performer_id = self._create_performer(performer)
                                if performer_id:
                                    applied_changes.append(f"Created performer: '{performer}'")
                                    if self.colorize:
                                        message = f"Missing Performer: '{performer}' ({Colors.GREEN}[+]{Colors.RESET} created in Stash)"
                                    else:
                                        message = f"Missing Performer: '{performer}' ([+] created in Stash)"
                                    
                                    # Add performer ID to list for scene update
                                    performer_ids_to_add.append(performer_id)
                                else:
                                    if self.colorize:
                                        message = f"Missing Performer: '{performer}' ({Colors.RED}[!]{Colors.RESET} failed to create in Stash)"
                                    else:
                                        message = f"Missing Performer: '{performer}' ([!] failed to create in Stash)"
                            else:
                                if self.colorize:
                                    message = f"Missing Performer: '{performer}' ({Colors.RED}[!]{Colors.RESET} does NOT exist in Stash - needs to be created)"
                                else:
                                    message = f"Missing Performer: '{performer}' ([!] does NOT exist in Stash - needs to be created)"
                        
                        logger.warning(f"Scene missing performer: '{performer}'")
                        # Add to differences list for formatted output
                        missing_performers.append(message)
                
                # Apply performer updates if necessary
                if self.apply_changes and not self.dry_run and performer_ids_to_add:
                    # Get current performer IDs
                    current_performer_ids = [p.get('id') for p in scene.get('performers', []) if p.get('id')]
                    
                    # Add new performers while keeping existing ones
                    all_performer_ids = current_performer_ids + performer_ids_to_add
                    
                    # Update the scene with the performers
                    if self._update_scene(scene['id'], {"performer_ids": all_performer_ids}):
                        applied_changes.append(f"Added {len(performer_ids_to_add)} performers to scene")
                        # Update messages to indicate performers were applied
                        for i, msg in enumerate(missing_performers):
                            if self.colorize:
                                missing_performers[i] = msg + f" ({Colors.GREEN}[✓]{Colors.RESET} applied to scene)"
                            else:
                                missing_performers[i] = msg + f" ([+] applied to scene)"
                    else:
                        # Update messages to indicate performer application failed
                        for i, msg in enumerate(missing_performers):
                            if self.colorize:
                                missing_performers[i] = msg + f" ({Colors.RED}[!]{Colors.RESET} failed to apply to scene)"
                            else:
                                missing_performers[i] = msg + f" ([!] failed to apply to scene)"
                
                # If there are missing performers, add them as a group
                if missing_performers:
                    differences.append({"type": "performers", "messages": missing_performers})
                
            # Check for detected tags if enabled
            if self.detect_tags and scene_path in ai_results and ai_results[scene_path].get('tags'):
                detected_tags = ai_results[scene_path].get('tags', [])
                if detected_tags:
                    # Get current scene tags
                    current_tags = [t.get('name', '') for t in scene.get('tags', [])]
                    
                    # Split detected tags into already applied and missing
                    already_applied = []
                    missing_tags = []
                    
                    for tag in detected_tags:
                        # Case-sensitive tag comparison
                        if tag in current_tags:
                            already_applied.append(tag)
                        else:
                            # Double-check if it's just a capitalization issue
                            tag_lower = tag.lower()
                            if any(t.lower() == tag_lower for t in current_tags):
                                # If it's just capitalization, get the correctly capitalized version from current tags
                                correct_tag = next(t for t in current_tags if t.lower() == tag_lower)
                                logger.debug(f"Tag capitalization mismatch: '{tag}' vs '{correct_tag}' - using current tag capitalization")
                                already_applied.append(correct_tag)
                            else:
                                missing_tags.append(tag)
                    
                    # Track tag IDs to add to the scene
                    tag_ids_to_add = []
                    
                    # Format tag messages and prepare for updates
                    missing_tag_messages = []
                    applied_tag_messages = []
                    
                    # Handle missing tags
                    for tag in missing_tags:
                        tag_exists = self._tag_exists_in_stash(tag, tag_list)
                        tag_id = None
                        
                        if tag_exists:
                            tag_id = self._get_tag_id(tag, tag_list)
                            if self.colorize:
                                missing_tag_messages.append(f"{Colors.CYAN}{tag}{Colors.RESET} ({Colors.GREEN}[✓]{Colors.RESET} exists)")
                            else:
                                missing_tag_messages.append(f"{tag} ([+] exists)")
                                
                            if tag_id:
                                tag_ids_to_add.append(tag_id)
                        else:
                            if self.create_missing and not self.dry_run:
                                tag_id = self._create_tag(tag)
                                if tag_id:
                                    applied_changes.append(f"Created tag: '{tag}'")
                                    if self.colorize:
                                        missing_tag_messages.append(f"{Colors.CYAN}{tag}{Colors.RESET} ({Colors.GREEN}[+]{Colors.RESET} created)")
                                    else:
                                        missing_tag_messages.append(f"{tag} ([+] created)")
                                        
                                    tag_ids_to_add.append(tag_id)
                                else:
                                    if self.colorize:
                                        missing_tag_messages.append(f"{Colors.CYAN}{tag}{Colors.RESET} ({Colors.RED}[!]{Colors.RESET} failed to create)")
                                    else:
                                        missing_tag_messages.append(f"{tag} ([!] failed to create)")
                            else:
                                if self.colorize:
                                    missing_tag_messages.append(f"{Colors.CYAN}{tag}{Colors.RESET} ({Colors.RED}[!]{Colors.RESET} missing)")
                                else:
                                    missing_tag_messages.append(f"{tag} ([!] missing)")
                    
                    # Format already applied tags
                    for tag in already_applied:
                        if self.colorize:
                            applied_tag_messages.append(f"{Colors.GREEN}{tag}{Colors.RESET}")
                        else:
                            applied_tag_messages.append(f"{tag} [✓]")
                    
                    # Log all detected tags
                    logger.info(f"Detected tags: {', '.join(detected_tags)}")
                    if missing_tags:
                        logger.info(f"Missing tags: {', '.join(missing_tags)}")
                    if already_applied:
                        logger.info(f"Already applied tags: {', '.join(already_applied)}")
                    
                    # Apply tag updates if necessary
                    if self.apply_changes and not self.dry_run and tag_ids_to_add:
                        # Get current tag IDs
                        current_tag_ids = [t.get('id') for t in scene.get('tags', []) if t.get('id')]
                        
                        # Add new tags while keeping existing ones
                        all_tag_ids = current_tag_ids + tag_ids_to_add
                        
                        # Update the scene with the tags
                        if self._update_scene(scene['id'], {"tag_ids": all_tag_ids}):
                            applied_changes.append(f"Added {len(tag_ids_to_add)} tags to scene")
                            # No need to update tag messages as they're already formatted with status
                        else:
                            # Update messages to indicate tag application failed
                            for i, msg in enumerate(missing_tag_messages):
                                if "([+] exists)" in msg or "([+] created)" in msg:
                                    if self.colorize:
                                        missing_tag_messages[i] = msg.replace("([+] exists)", f"({Colors.RED}[!]{Colors.RESET} failed to apply)")
                                        missing_tag_messages[i] = msg.replace("([+] created)", f"({Colors.RED}[!]{Colors.RESET} failed to apply)")
                                    else:
                                        missing_tag_messages[i] = msg.replace("([+] exists)", "([!] failed to apply)")
                                        missing_tag_messages[i] = msg.replace("([+] created)", "([!] failed to apply)")
                    
                    # Add to differences if there are detected tags
                    if missing_tags or already_applied:
                        differences.append({"type": "tags", "missing": missing_tag_messages, "applied": applied_tag_messages})
            
            # Check for HTML in scene details if detect_details is enabled
            if self.detect_details and scene.get('details'):
                original_details = scene.get('details', '')
                logger.debug(f"Original details for scene {scene.get('id')}:\n{original_details}")
                
                cleaned_details = self._strip_html(original_details)
                logger.debug(f"Cleaned details for scene {scene.get('id')}:\n{cleaned_details}")
                
                # If the cleaned details are different from the original
                if cleaned_details != original_details:
                    has_differences = True
                    
                    # Format the difference message
                    original_len = len(original_details)
                    cleaned_len = len(cleaned_details)
                    percentage_decrease = ((original_len - cleaned_len) / original_len * 100) if original_len > 0 else 0
                    
                    if self.colorize:
                        message = f"{Colors.YELLOW}HTML detected in scene details.{Colors.RESET} ({original_len} chars → {cleaned_len} chars, {percentage_decrease:.1f}% decrease)"
                    else:
                        message = f"HTML detected in scene details. ({original_len} chars → {cleaned_len} chars, {percentage_decrease:.1f}% decrease)"
                        
                    # Add to differences list
                    differences.append({"type": "details", "message": message, "original": original_details, "cleaned": cleaned_details})
                    
                    # Apply changes if requested
                    if self.apply_changes and not self.dry_run:
                        if self._update_scene(scene['id'], {"details": cleaned_details}):
                            applied_changes.append("Removed HTML from scene details")
                            if self.colorize:
                                message += f" ({Colors.GREEN}[✓]{Colors.RESET} fixed)"
                            else:
                                message += f" ([+] fixed)"
                        else:
                            if self.colorize:
                                message += f" ({Colors.RED}[!]{Colors.RESET} failed to update)"
                            else:
                                message += f" ([!] failed to update)"
            
            # Add marker tag if specified and not in dry run mode
            if self.mark_tag and not self.dry_run and self.apply_changes:
                # Add the marker tag to indicate this scene has been processed
                if self._add_mark_tag_to_scene(scene['id'], scene.get('tags', []), self.mark_tag):
                    applied_changes.append(f"Added marker tag: '{self.mark_tag}' to scene")
            
            # Output formatted differences
            if not verbose and differences:
                separator = "=" * 50
                if self.colorize:
                    print(f"\n{Colors.YELLOW}{separator}{Colors.RESET}")
                    print(f"{Colors.BOLD}{Colors.YELLOW}[!] Metadata Issues Detected:{Colors.RESET}")
                    print(f"{Colors.YELLOW}{separator}{Colors.RESET}")
                    
                    for diff in differences:
                        if diff["type"] == "studio":
                            print(f"\n* {diff['message']}")
                        elif diff["type"] == "performers":
                            print(f"\n* {Colors.BOLD}Missing Performers:{Colors.RESET}")
                            for i, performer_msg in enumerate(diff["messages"]):
                                print(f"  {i+1}. {performer_msg}")
                        elif diff["type"] == "tags":
                            print(f"\n* {Colors.BOLD}Tags:{Colors.RESET}")
                            if diff.get("missing"):
                                print(f"  {Colors.BOLD}Missing Tags:{Colors.RESET} {', '.join(diff['missing'])}")
                            if diff.get("applied"):
                                print(f"  {Colors.BOLD}Already Applied:{Colors.RESET} {', '.join(diff['applied'])}")
                        elif diff["type"] == "details":
                            print(f"\n* {Colors.BOLD}Scene Details:{Colors.RESET}")
                            print(f"  {diff['message']}")
                            
                            # Show a preview of the changes (truncated)
                            if logger.level <= logging.INFO:
                                max_preview = 100  # Maximum length for preview
                                
                                # Truncate the original and cleaned for preview if needed
                                orig_preview = diff['original'][:max_preview] + ('...' if len(diff['original']) > max_preview else '')
                                clean_preview = diff['cleaned'][:max_preview] + ('...' if len(diff['cleaned']) > max_preview else '')
                                
                                print(f"  {Colors.BOLD}Original:{Colors.RESET} {orig_preview}")
                                print(f"  {Colors.BOLD}Cleaned:{Colors.RESET} {clean_preview}")
                    
                    # Print summary of applied changes if any
                    if applied_changes and not self.dry_run:
                        print(f"\n{Colors.GREEN}{separator}{Colors.RESET}")
                        print(f"{Colors.BOLD}{Colors.GREEN}[+] Changes Applied:{Colors.RESET}")
                        print(f"{Colors.GREEN}{separator}{Colors.RESET}")
                        for change in applied_changes:
                            print(f"* {change}")
                                
                    print(f"\n{Colors.YELLOW}{separator}{Colors.RESET}")
                else:
                    print(f"\n{separator}")
                    print(f"[!] Metadata Issues Detected:")
                    print(f"{separator}")
                    
                    for diff in differences:
                        if diff["type"] == "studio":
                            print(f"\n* {diff['message']}")
                        elif diff["type"] == "performers":
                            print(f"\n* Missing Performers:")
                            for i, performer_msg in enumerate(diff["messages"]):
                                print(f"  {i+1}. {performer_msg}")
                        elif diff["type"] == "tags":
                            print(f"\n* Tags:")
                            if diff.get("missing"):
                                print(f"  Missing Tags: {', '.join(diff['missing'])}")
                            if diff.get("applied"):
                                print(f"  Already Applied: {', '.join(diff['applied'])}")
                        elif diff["type"] == "details":
                            print(f"\n* Scene Details:")
                            print(f"  {diff['message']}")
                            
                            # Show a preview of the changes (truncated)
                            if logger.level <= logging.INFO:
                                max_preview = 100  # Maximum length for preview
                                
                                # Truncate the original and cleaned for preview if needed
                                orig_preview = diff['original'][:max_preview] + ('...' if len(diff['original']) > max_preview else '')
                                clean_preview = diff['cleaned'][:max_preview] + ('...' if len(diff['cleaned']) > max_preview else '')
                                
                                print(f"  Original: {orig_preview}")
                                print(f"  Cleaned: {clean_preview}")
                    
                    # Print summary of applied changes if any
                    if applied_changes and not self.dry_run:
                        print(f"\n{separator}")
                        print(f"[+] Changes Applied:")
                        print(f"{separator}")
                        for change in applied_changes:
                            print(f"* {change}")
                                
                    print(f"\n{separator}")
            elif not has_differences and not verbose:
                separator = "-" * 50
                if self.colorize:
                    print(f"\n{Colors.GREEN}[✓] No metadata issues detected - scene looks good!{Colors.RESET}")
                    print(f"{Colors.BLUE}{separator}{Colors.RESET}")
                else:
                    print(f"\n[+] No metadata issues detected - scene looks good!")
                    print(f"{separator}")
    
    def _estimate_openai_cost(self, scenes, batch_size=15):
        "Estimate the cost of OpenAI API calls for the given scenes."
        if not scenes:
            return
        
        # Cost constants (in USD per 1M tokens, as of May 2023)
        INPUT_COST_PER_MILLION = 0.50    # $0.50 per 1M input tokens for gpt-3.5-turbo-16k
        OUTPUT_COST_PER_MILLION = 1.50   # $1.50 per 1M output tokens for gpt-3.5-turbo-16k
        
        # Token estimation (rough approximations)
        AVG_TOKENS_PER_CHAR = 0.25       # Average tokens per character in the prompt
        BASE_PROMPT_CHARS = 1000         # Base prompt size in characters (instructions, etc.)
        AVG_CHARS_PER_PATH = 150         # Average characters per file path
        AVG_CHARS_PER_TITLE = 50         # Average characters per title if using titles
        AVG_CHARS_PER_ALIAS = 20         # Average characters per performer alias in the prompt
        ESTIMATED_OUTPUT_TOKENS = 150    # Estimated output tokens per scene
        
        # Calculate number of batches
        num_batches = (len(scenes) + batch_size - 1) // batch_size
        
        # Estimate total characters in prompts
        total_chars = num_batches * BASE_PROMPT_CHARS
        total_chars += len(scenes) * AVG_CHARS_PER_PATH
        if self.use_titles:
            total_chars += len(scenes) * AVG_CHARS_PER_TITLE
            
        # Add performer aliases (limited to 100 per batch)
        try:
            performers = self._get_all_performers()
            alias_count = 0
            for performer in performers:
                aliases = performer.get('aliases', '')
                if isinstance(aliases, str):
                    alias_count += len([a for a in aliases.split(',') if a.strip()])
                elif isinstance(aliases, list):
                    alias_count += len(aliases)
            
            # Limit aliases to 100 per batch
            alias_chars = min(100, alias_count) * AVG_CHARS_PER_ALIAS * num_batches
            total_chars += alias_chars
            
        except Exception:
            # If we can't get aliases, just use a rough estimate
            total_chars += 1000 * num_batches
        
        # Convert to tokens
        estimated_input_tokens = total_chars * AVG_TOKENS_PER_CHAR
        estimated_output_tokens = ESTIMATED_OUTPUT_TOKENS * len(scenes)
        
        # Calculate costs
        input_cost = (estimated_input_tokens / 1000000) * INPUT_COST_PER_MILLION
        output_cost = (estimated_output_tokens / 1000000) * OUTPUT_COST_PER_MILLION
        total_cost = input_cost + output_cost
        
        # Log the estimates (use warning level so they show in dry-run mode with default log level)
        if self.dry_run:
            # In dry-run mode, show cost estimates prominently
            print(f"\nEstimated OpenAI API usage:")
            print(f"  - OpenAI model: {self.openai_model}")
            print(f"  - Scenes to process: {len(scenes)}")
            print(f"  - Batch size: {batch_size} scenes per API call")
            print(f"  - Number of API calls: {num_batches}")
            print(f"  - Estimated input tokens: {estimated_input_tokens:.0f} (${input_cost:.4f})")
            print(f"  - Estimated output tokens: {estimated_output_tokens:.0f} (${output_cost:.4f})")
            print(f"  - Estimated total cost: ${total_cost:.4f} USD")
            print(f"  (These are rough estimates and actual costs may vary)\n")
        else:
            # In normal mode, use logger
            logger.info(f"Estimated OpenAI API usage:")
            logger.info(f"  - OpenAI model: {self.openai_model}")
            logger.info(f"  - Scenes to process: {len(scenes)}")
            logger.info(f"  - Batch size: {batch_size} scenes per API call")
            logger.info(f"  - Number of API calls: {num_batches}")
            logger.info(f"  - Estimated input tokens: {estimated_input_tokens:.0f} (${input_cost:.4f})")
            logger.info(f"  - Estimated output tokens: {estimated_output_tokens:.0f} (${output_cost:.4f})")
            logger.info(f"  - Estimated total cost: ${total_cost:.4f} USD")
            logger.info("  (These are rough estimates and actual costs may vary)")
    
    def _batch_detect_with_ai(self, scenes, batch_size=15):
        "Process multiple scenes with a single API call to save tokens and time."
        if not self.openai_client:
            return {}
            
        # Prepare results dictionary
        results = {}
        
        # Get all performer aliases from Stash - ONLY using aliases stored in Stash, not generating from names
        performer_alias_info = []
        no_aliases_found = True  # Track if we find any aliases at all
        alias_counter = {}  # Track how many performers have each alias
        temp_aliases = []  # Temporary storage for aliases before filtering duplicates
        
        # Note: We don't need to fetch tags here anymore, as it's already done in analyze_scenes
        # when detect_tags is enabled. This is to avoid duplicate API calls.
        tag_list = []
        
        try:
            performers = self._get_all_performers()
            
            # First pass: collect all aliases and count occurrences
            for performer in performers:
                name = performer.get('name', '')
                aliases = performer.get('aliases', '')
                
                # Handle aliases as string (comma-separated) or list
                if isinstance(aliases, str):
                    alias_list = [a.strip() for a in aliases.split(',') if a.strip()]
                elif isinstance(aliases, list):
                    alias_list = [a for a in aliases if a]
                else:
                    alias_list = []
                
                # Only process aliases that are actually stored in Stash
                if name and alias_list:
                    # Filter out aliases that exactly match the performer name
                    filtered_alias_list = [alias for alias in alias_list if alias.lower() != name.lower()]
                    
                    if filtered_alias_list:  # If we have any aliases left after filtering
                        no_aliases_found = False  # We found at least one valid alias
                        
                        # Count occurrences of each alias
                        for alias in filtered_alias_list:
                            if alias:  # Skip empty aliases
                                # Convert to lowercase for counting (case-insensitive comparison)
                                alias_lower = alias.lower()
                                if alias_lower in alias_counter:
                                    alias_counter[alias_lower] += 1
                                else:
                                    alias_counter[alias_lower] = 1
                                
                                # Store in temporary list with original case
                                temp_aliases.append({
                                    "performer": name,
                                    "alias": alias,
                                    "alias_lower": alias_lower
                                })
            
            # Second pass: only keep aliases unique to one performer
            for alias_data in temp_aliases:
                if alias_counter[alias_data["alias_lower"]] == 1:  # Only include if unique
                    # Sort aliases: prioritize lowercase ones first (sorting done at prompt generation)
                    performer_alias_info.append({
                        "performer": alias_data["performer"],
                        "alias": alias_data["alias"]
                    })
                    
            if performer_alias_info:
                logger.debug(f"Found {len(performer_alias_info)} unique aliases for {len(performers)} performers")
                if len(temp_aliases) > len(performer_alias_info):
                    logger.debug(f"Filtered out {len(temp_aliases) - len(performer_alias_info)} duplicate aliases")
            else:
                logger.debug("No unique aliases found after filtering")
                no_aliases_found = True
            
            # If we couldn't find any aliases in Stash or all were filtered, notify the user
            if no_aliases_found and performers:
                if temp_aliases:  # We had aliases but all were duplicates
                    logger.warning("All performer aliases were assigned to multiple performers and were filtered out. Consider adding unique aliases in Stash.")
                    # Include a note about this in performer_alias_info to show in prompt
                    performer_alias_info.append({
                        "performer": "NOTE", 
                        "alias": "All aliases were assigned to multiple performers and filtered out. Consider adding unique aliases in Stash."
                    })
                else:  # No aliases at all
                    logger.warning("No performer aliases found in Stash. Consider adding aliases in Stash for better performer detection.")
                    # Include a note about this in performer_alias_info to show in prompt
                    performer_alias_info.append({
                        "performer": "NOTE", 
                        "alias": "No performer aliases found in Stash database. Performance may be reduced."
                    })
        except Exception as e:
            print(f"Warning: Error retrieving performer aliases: {e}")
        
        # Process scenes in batches
        scene_batches = [scenes[i:i+batch_size] for i in range(0, len(scenes), batch_size)]
        
        # Log which model is being used
        logger.info(f"Using OpenAI model {self.openai_model} for analysis")
        
        for batch_index, scene_batch in enumerate(scene_batches):
            try:
                file_paths = [scene['file_path'] for scene in scene_batch]
                scene_titles = [scene.get('title', '') for scene in scene_batch]
                
                # Construct batch prompt
                # Construct batch prompt
                prompt = "Analyze the following list of adult content filepaths"
                
                # Add details about what's being analyzed
                if self.use_titles:
                    prompt += " and titles"
                if self.use_details:
                    prompt += " and descriptions"
                if self.use_studio:
                    prompt += " and current studio information"
                
                # What we're identifying
                prompt += " to identify "
                
                # Build the identification part
                identify_parts = []
                if self.detect_studios:
                    identify_parts.append("studios")
                if self.detect_performers:
                    identify_parts.append("performers")
                if self.detect_tags:
                    identify_parts.append("tags")
                if not identify_parts:
                    identify_parts.append("content")
                
                prompt += " and ".join(identify_parts) + ".\n"
                
                # Add what to determine for each entry
                entry_type = "entry" if self.use_titles or self.use_details else "path"
                prompt += f"For each {entry_type}, determine:\n"
                
                # Add numbered items
                item_number = 0
                
                # Studio determination
                if self.detect_studios:
                    item_number += 1
                    prompt += f"{item_number}. The studio name (the PRODUCTION COMPANY, like 'Sean Cody', 'Lucas Entertainment', 'Raw Fuck Club', etc.)\n"
                
                # Performer determination
                if self.detect_performers:
                    item_number += 1
                    prompt += f"{item_number}. The performer names (actual performers, not descriptions)\n"
                
                # Tag determination
                if self.detect_tags:
                    item_number += 1
                    prompt += f"{item_number}. Relevant tags from the provided tag list that accurately describe the content\n"
                
                # Add studio detection rules if studio detection is enabled
                if self.detect_studios:
                    prompt += (
                        "\nIMPORTANT STUDIO DETECTION RULES:"
                        "\n- A studio is a PRODUCTION COMPANY, not a performer name or series title"
                        "\n- ONLY assign a studio when you're absolutely confident it's a production company"
                        "\n- Studios are typically found in directory names, not in the filename itself"
                        "\n- Common studios include: \"Sean Cody\", \"Men.com\", \"Tim Tales\", \"Raw Fuck Club\", etc."
                        "\n- If unsure whether something is a studio or performer, leave the studio as null"
                        "\n- DO NOT assign a performer name as a studio unless the performer definitely has their own studio"
                        "\n- Example: If a path is \"/data/Amir Fuxxx - Adventures in Porn/file.mp4\", the studio is likely null, not \"Amir Fuxxx\""
                    )
                
                # Add performer detection rules if performer detection is enabled
                if self.detect_performers:
                    prompt += (
                        "\nCRITICAL PERFORMER DETECTION RULES - READ CAREFULLY:"
                        "\n- The \"performers\" array MUST ONLY contain names with BOTH first AND last names clearly identifiable"
                        "\n- NEVER include single-word names in the \"performers\" array (even if they seem like a full name)"
                        "\n- EXAMPLES of valid performer entries: \"John Smith\", \"Beau Butler\", \"Alex Adams\""
                        "\n- EXAMPLES of INVALID performer entries: \"Brad\", \"Diesel\", \"Apollo\", \"Rex\", \"Max\""
                        "\n- ALL single-word names MUST go in the \"matched_aliases\" array instead"
                        "\n- If a path like \"/videos/Brad/scene.mp4\" only has \"Brad\", put \"Brad\" in matched_aliases, NOT in performers"
                        "\n- Any word that starts with @ in the path or description (like @nickbutterx) MUST be included in matched_aliases"
                        "\n- This strict requirement ensures proper metadata tagging - it\'s the most important rule to follow"
                        "\n- When in doubt, put a name in \"matched_aliases\" instead of \"performers\""
                    )
                
                # Add general guidelines
                prompt += (
                    "\nBe conservative - only include studios and performers you're confident about."
                    "\nIgnore descriptive terms like \"hairy\", \"muscle\", etc."
                )
                
                # Add additional context information if enabled
                if self.use_titles:
                    prompt += "\nWhen provided, use the scene titles for additional context as they often contain studio and performer information."
                    
                if self.use_details:
                    prompt += "\nWhen provided, use the scene descriptions for additional context as they often contain studio and performer information in more detail."
                    
                if self.use_studio:
                    prompt += "\nWhen provided, use the current studio information as context. If the current studio appears correct, do not change it unless you have strong evidence of a better match."
                
                # Add formatting rules
                prompt += (
                    "\nIMPORTANT FORMATTING RULES:"
                    "\n- Format studio names properly with appropriate spacing and capitalization"
                    "\n- For example, \"rawfuckclub\" should be \"Raw Fuck Club\" and \"barebackcumpigs\" should be \"Bareback Cum Pigs\""
                    "\n- Use proper capitalization for performer names (like \"John Smith\" not \"john smith\")"
                    "\n- You may try to convert usernames or directory names to performer names when appropriate"
                    "\n- For example, a username like \"beaubutlerxxx\" might represent performer \"Beau Butler\""
                )
                
                
                # Add performer aliases section if performer detection is enabled
                if self.detect_performers:
                    prompt += (
                        "\nPERFORMER ALIASES:"
                        "\n* Here's a list of performer aliases from our database to check against:"
                    )
                
                # Add performer aliases (up to a reasonable limit for the prompt size)
                if self.detect_performers and performer_alias_info:
                    # Check if we're just showing the "no aliases" note
                    if len(performer_alias_info) == 1 and performer_alias_info[0]['performer'] == 'NOTE':
                        prompt += f"\n- {performer_alias_info[0]['alias']}"
                    else:
                        # Sort the performer_alias_info list to prioritize lowercase aliases
                        performer_alias_info.sort(
                            key=lambda x: (0 if all(c.islower() or not c.isalpha() for c in x['alias']) else 1, x['alias'].lower())
                        )
                        
                        alias_limit = min(100, len(performer_alias_info))
                        for i, alias_data in enumerate(performer_alias_info[:alias_limit]):
                            # Skip the note if it's mixed with real aliases
                            if alias_data['performer'] != 'NOTE':
                                # Present the alias exactly as stored, preserving case
                                prompt += f"\n- \"{alias_data['alias']}\" is an alias for \"{alias_data['performer']}\""
                        
                        if len(performer_alias_info) > alias_limit:
                            prompt += f"\n- Plus {len(performer_alias_info) - alias_limit} more aliases (not shown due to size constraints)"
                elif self.detect_performers:
                    prompt += "\n- No performer aliases found in the Stash database"
                
                # Add tag detection rules and list if enabled
                if self.detect_tags:
                    prompt += (
                        "\nTAG DETECTION RULES:"
                        "\n- Only assign tags you are confident apply to the content"
                        "\n- CRITICAL: Tags are CASE SENSITIVE - you MUST use the exact capitalization shown in the list"
                        "\n- Example: If the tag list shows \"bareback\" (not \"Bareback\"), you must use \"bareback\""
                        "\n- Base your tag selections on information in the filepath, title, and description (if available)"
                        "\n- You may assign multiple tags, but only if you have high confidence"
                        "\n- If you're unsure about a tag, do not include it"
                        "\n- Example: If a path contains 'barebacking', assign the 'bareback' tag"
                        "\n- Example: If a description states 'outdoor scene', assign the 'outdoor' tag"
                        "\n- Do not assign generic tags like 'porn' or 'adult' - be specific"
                        "\n- Never invent new tags or modify the capitalization of existing tags"
                        "\nTAG LIST (only use tags from this list with EXACT capitalization):"
                    )
                    
                    # Add tag list if available
                    if tag_list:
                        # Sort tags alphabetically
                        sorted_tags = sorted(tag_list, key=lambda t: t.get('name', '').lower())
                        
                        # Add tags to the prompt, including descriptions if available
                        tag_limit = 300  # Limit the number of tags to avoid extremely large prompts
                        tags_added = 0
                        
                        for tag in sorted_tags[:tag_limit]:
                            tag_name = tag.get('name', '')
                            if tag_name:
                                # Add description if available and not too long
                                tag_desc = tag.get('description', '')
                                if tag_desc and len(tag_desc) > 100:
                                    tag_desc = tag_desc[:97] + "..."
                                    
                                if tag_desc:
                                    prompt += f"\n- {tag_name}: {tag_desc}"
                                else:
                                    prompt += f"\n- {tag_name}"
                                tags_added += 1
                        
                        # Note if we had to limit the tags
                        if len(sorted_tags) > tag_limit:
                            prompt += f"\n- Plus {len(sorted_tags) - tag_limit} more tags (not shown due to size constraints)"
                            
                        logger.debug(f"Added {tags_added} tags to the prompt")
                    else:
                        prompt += "\n- No tags found in the Stash database"
                
                # Add performer matching instructions if enabled
                if self.detect_performers:
                    prompt += """
                    
                    - Check for matches between these performer names and the content in the path or title
                    - You can also try to intelligently convert usernames to potential performer names
                    - For example, a path like "/ofscraper/beaubutlerxxx/" might indicate performer "Beau Butler"
                    """
                
                prompt += """
                The filepaths to analyze are:
                """
                
                # Prepare scene details
                scene_details = [scene.get('details', '') for scene in scene_batch]
                scene_studios = [scene.get('studio', {}).get('name', '') if scene.get('studio') else '' for scene in scene_batch]
                
                # Add each path with index, title, details, and studio if enabled
                for i, path in enumerate(file_paths):
                    prompt += f"\n{i+1}. Path: {path}"
                    
                    if self.use_titles and scene_titles[i]:
                        prompt += f"\n   Title: {scene_titles[i]}"
                        
                    if self.use_details and scene_details[i]:
                        # Truncate very long descriptions to keep prompt size reasonable
                        details = scene_details[i]
                        if len(details) > 500:  # Limit super long descriptions
                            details = details[:497] + "..."
                        prompt += f"\n   Description: {details}"
                    
                    if self.use_studio and scene_studios[i]:
                        prompt += f"\n   Current Studio: {scene_studios[i]}"
                
                prompt += "\nReturn your analysis as a JSON object where each key is the full filepath, and each value is an object with:"
                
                # Add studio field based on detect_studios setting
                if self.detect_studios:
                    prompt += "\n- \"studio\": The studio name properly formatted (or null if none detected)"
                else:
                    prompt += "\n- \"studio\": null"
                    
                # Add performer fields based on detect_performers setting
                if self.detect_performers:
                    prompt += (
                        "\n- \"performers\": STRICT: Array ONLY containing names with TWO OR MORE WORDS (first AND last name)"
                        "\n  * MUST have space between first/last name"
                        "\n  * MUST NEVER contain single-word names"
                        "\n  * If unsure if a name has both parts, DO NOT include it here"
                        "\n  * Leave as empty array [] if no multi-word performer names are detected"
                        "\n- \"matched_aliases\": Array containing:"
                        "\n  * Any aliases from the provided list that were found"
                        "\n  * ANY and ALL single-word performer names (like \"Brad\", \"Max\", etc.)"
                        "\n  * ANY names you're not 100% sure have both first and last parts"
                    )
                else:
                    prompt += (
                        "\n- \"performers\": []"
                        "\n- \"matched_aliases\": []"
                    )
                
                # Add tags field based on detect_tags setting
                if self.detect_tags:
                    prompt += (
                        "\n- \"tags\": Array of relevant tags from the provided tag list that accurately describe the content"
                        "\n  * ONLY include tags from the provided list with EXACT capitalization"
                        "\n  * Tags are CASE SENSITIVE - use the exact capitalization shown in the tag list"
                        "\n  * ONLY include tags you are confident apply to the content"
                        "\n  * If unsure about a tag, do not include it"
                    )
                else:
                    prompt += "\n- \"tags\": []"
                
                prompt += "\nExample response format - PAY CLOSE ATTENTION:"
                prompt += "\n{"
                
                # Construct example 1
                prompt += "\n    \"/path/to/file1.mp4\": {"
                if self.detect_studios:
                    prompt += "\n        \"studio\": \"Raw Fuck Club\","
                else:
                    prompt += "\n        \"studio\": null,"
                    
                if self.detect_performers:
                    prompt += "\n        \"performers\": [\"Miguel Rey\", \"Dan Edwards\"], // CORRECT: two-word names only"
                    prompt += "\n        \"matched_aliases\": [\"miguelx\", \"danny_ed\"]"
                else:
                    prompt += "\n        \"performers\": [],"
                    prompt += "\n        \"matched_aliases\": []"
                    
                if self.detect_tags:
                    prompt += "\n        \"tags\": [\"Bareback\", \"Blowjob\", \"Threesome\"] // EXACT capitalization (case sensitive!)"
                
                # Close the first example
                prompt += "\n    },"
                
                # Construct example 2
                prompt += "\n    \"/path/to/Brad/file2.mp4\": {"
                if self.detect_studios:
                    prompt += "\n        \"studio\": \"Sean Cody\","
                else:
                    prompt += "\n        \"studio\": null,"
                
                prompt += "\n        \"performers\": [], // CORRECT: empty because only single-word name \"Brad\" is present"
                
                if self.detect_performers:
                    prompt += "\n        \"matched_aliases\": [\"Brad\", \"Jess\", \"Diesel\"]"
                else:
                    prompt += "\n        \"matched_aliases\": []"
                    
                if self.detect_tags:
                    prompt += "\n        \"tags\": [\"Masturbation\", \"Solo\", \"POV\"] // Use EXACT tag case as shown in list"
                 
                # Close the second example   
                prompt += "\n    },"
                    
                # Construct example 3
                prompt += "\n    \"/path/to/Brad Johnson/file3.mp4\": {"
                prompt += "\n        \"studio\": null,"
                
                if self.detect_performers:
                    prompt += "\n        \"performers\": [\"Brad Johnson\"], // CORRECT: two-word name"
                    prompt += "\n        \"matched_aliases\": [\"Apollo\"]"
                else:
                    prompt += "\n        \"performers\": [],"
                    prompt += "\n        \"matched_aliases\": []"
                    
                if self.detect_tags:
                    prompt += "\n        \"tags\": [\"Outdoor\", \"Kissing\", \"Public\"] // Case matters! Match tags exactly"
                
                # Close the third example and the entire examples section
                prompt += "\n    }"
                prompt += "\n}"
                
                logger.info(f"Processing batch {batch_index+1}/{len(scene_batches)} ({len(file_paths)} files)...")
                
                # Log the full prompt in debug mode or if show_prompts is enabled
                if logger.isEnabledFor(logging.DEBUG) or self.show_prompts:
                    # If show_prompts is enabled, always show the full prompt
                    if self.show_prompts:
                        print(f"\nOpenAI Batch Prompt (showing full prompt):\n{'-' * 80}\n{prompt}\n{'-' * 80}\n")
                    # Debug mode with truncation if needed
                    elif logger.isEnabledFor(logging.DEBUG):
                        # Truncate the prompt if it's too long for logging
                        max_log_length = 2000
                        if len(prompt) > max_log_length:
                            # Get the first part and the last 10 lines of the prompt
                            prompt_first_part = prompt[:max_log_length]
                            prompt_last_lines = '\n'.join(prompt.splitlines()[-10:])
                            
                            truncated_prompt = f"{prompt_first_part}\n\n[...truncated, total length: {len(prompt)} chars]\n\nLast 10 lines of the prompt:\n{prompt_last_lines}"
                            logger.debug(f"OpenAI prompt (truncated):\n{truncated_prompt}")
                        else:
                            logger.debug(f"OpenAI prompt:\n{prompt}")
                
                # Make API call
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                # Parse results
                result_text = response.choices[0].message.content.strip()
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"OpenAI batch detection response:\n{result_text}")
                    
                batch_results = json.loads(result_text)
                
                # Validate and merge results
                for path in file_paths:
                    if path in batch_results:
                        path_result = batch_results[path]
                        if isinstance(path_result, dict):
                            # Ensure studio is string or None
                            studio = path_result.get('studio')
                            if studio and not isinstance(studio, str):
                                studio = str(studio)
                                
                            # Ensure performers is a list of strings with first and last names
                            performers = path_result.get('performers', [])
                            if not isinstance(performers, list):
                                performers = []
                            
                            # Only keep performers with at least two words (first and last name)
                            valid_performers = []
                            single_names = []
                            for p in performers:
                                if not p or not isinstance(p, str):
                                    continue
                                    
                                # Check if name has at least two words (first and last name)
                                name_parts = p.strip().split()
                                if len(name_parts) >= 2:
                                    valid_performers.append(p)
                                else:
                                    # If it's a single name, move it to matched_aliases
                                    single_names.append(p)
                                    logger.debug(f"Moving single-name performer '{p}' to matched_aliases")
                            
                            performers = valid_performers
                            
                            # Extract matched aliases if available
                            matched_aliases = path_result.get('matched_aliases', [])
                            if not isinstance(matched_aliases, list):
                                matched_aliases = []
                            matched_aliases = [a for a in matched_aliases if a and isinstance(a, str)]
                            
                            # Add any single-name performers that were moved from performers list
                            for single_name in single_names:
                                if single_name not in matched_aliases:
                                    matched_aliases.append(single_name)
                                    
                            # Extract tags if tag detection is enabled
                            detected_tags = []
                            if self.detect_tags:
                                tags = path_result.get('tags', [])
                                if isinstance(tags, list):
                                    detected_tags = [t for t in tags if t and isinstance(t, str)]
                                    if detected_tags:
                                        logger.info(f"Detected tags for {os.path.basename(path)}: {', '.join(detected_tags)}")
                            
                            # Store the result
                            scene_result = {
                                'studio': studio,
                                'performers': performers,
                                'matched_aliases': matched_aliases
                            }
                            
                            # Add tags if tag detection is enabled
                            if self.detect_tags:
                                scene_result['tags'] = detected_tags
                            
                            results[path] = scene_result
                            
                            # Log the individual scene result in debug mode
                            logger.debug(f"AI detection result for {os.path.basename(path)}:\n{json.dumps(scene_result, indent=2)}")
                
            except Exception as e:
                logger.error(f"Error in batch {batch_index+1}: {e}")
                continue
                
        return results

            

    
    def _clean_name(self, name):
        "Cleans up extracted names by replacing underscores, dots, etc."
        if not name:
            logger.debug("Clean name called with empty name")
            return None
            
        logger.debug(f"Cleaning name: '{name}'")
        
        # Replace common separators with spaces
        cleaned = re.sub(r'[._-]', ' ', name)
        if cleaned != name:
            logger.debug(f"After separator replacement: '{cleaned}'")
        
        # Remove common extensions or suffixes
        name_without_ext = re.sub(r'(?i)\.(mp4|avi|mkv|mov|wmv)$', '', cleaned)
        if name_without_ext != cleaned:
            logger.debug(f"After extension removal: '{name_without_ext}'")
        
        # Clean up extra spaces
        name_clean_spaces = re.sub(r'\s+', ' ', name_without_ext).strip()
        if name_clean_spaces != name_without_ext:
            logger.debug(f"After space cleanup: '{name_clean_spaces}'")
        
        # Title case for consistency
        final_name = name_clean_spaces.title()
        if final_name != name_clean_spaces:
            logger.debug(f"After title case: '{final_name}'")
        
        logger.debug(f"Final cleaned name: '{final_name}'")
        return final_name
        
    def _strip_html(self, html_text):
        "Strips HTML tags from text, preserving links and line breaks."
        if not html_text:
            return html_text
        
        logger.debug("HTML cleaning process:")
        logger.debug(f"Original HTML ({len(html_text)} chars):\n{html_text}")
            
        # Replace <br> and <p> with newlines to preserve paragraph structure
        text = re.sub(r'<br\s*/?>|<p>|</p>', '\n', html_text)
        logger.debug(f"After replacing <br> and <p> tags ({len(text)} chars):\n{text}")
        
        # Extract href links with their text
        text = re.sub(r'<a\s+href=[\'"]([^\'"]+)[\'"][^>]*>([^<]+)</a>', r'\2 (\1)', text)
        logger.debug(f"After extracting links ({len(text)} chars):\n{text}")
        
        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        logger.debug(f"After removing all HTML tags ({len(text)} chars):\n{text}")
        
        # Fix any excess newlines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Decode HTML entities like &amp;, &quot;, etc.
        import html
        text = html.unescape(text)
        logger.debug(f"After decoding HTML entities ({len(text)} chars):\n{text}")
        
        # Normalize and trim whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        final_text = text.strip()
        logger.debug(f"Final cleaned text ({len(final_text)} chars):\n{final_text}")
        
        return final_text
        
    def _get_tag_ids(self, tag_names):
        "Fetch tag IDs by name."
        if not tag_names:
            return []
            
        tag_ids = []
        for tag_name in tag_names:
            try:
                query = (
                    "query FindTagByName($name: String!) {"
                    "  findTags(tag_filter: {name: {value: $name, modifier: EQUALS}}) {"
                    "    tags {"
                    "      id"
                    "      name"
                    "    }"
                    "  }"
                    "}"
                )
                result = self.stash.call_GQL(query, {"name": tag_name})
                tags = result.get('findTags', {}).get('tags', [])
                
                if tags:
                    # Find exact match if possible
                    exact_match = next((t['id'] for t in tags if t['name'].lower() == tag_name.lower()), None)
                    if exact_match:
                        tag_ids.append(exact_match)
                        logger.debug(f"Found tag ID for '{tag_name}': {exact_match}")
                    else:
                        # Use first match if no exact match
                        tag_ids.append(tags[0]['id'])
                        logger.debug(f"Using closest tag match for '{tag_name}': {tags[0]['name']} (ID: {tags[0]['id']})")
                else:
                    logger.warning(f"Tag '{tag_name}' not found")
            except Exception as e:
                logger.error(f"Error fetching tag ID for '{tag_name}': {e}")
                
        return tag_ids
    
    def _get_performer_ids(self, performer_names):
        "Fetch performer IDs by name."
        if not performer_names:
            return []
            
        performer_ids = []
        for performer_name in performer_names:
            try:
                query = (
                    "query FindPerformerByName($name: String!) {"
                    "  findPerformers(performer_filter: {name: {value: $name, modifier: EQUALS}}) {"
                    "    performers {"
                    "      id"
                    "      name"
                    "    }"
                    "  }"
                    "}"
                )
                result = self.stash.call_GQL(query, {"name": performer_name})
                performers = result.get('findPerformers', {}).get('performers', [])
                
                if performers:
                    # Find exact match if possible
                    exact_match = next((p['id'] for p in performers if p['name'].lower() == performer_name.lower()), None)
                    if exact_match:
                        performer_ids.append(exact_match)
                        logger.debug(f"Found performer ID for '{performer_name}': {exact_match}")
                    else:
                        # Use first match if no exact match
                        performer_ids.append(performers[0]['id'])
                        logger.debug(f"Using closest performer match for '{performer_name}': {performers[0]['name']} (ID: {performers[0]['id']})")
                else:
                    logger.warning(f"Performer '{performer_name}' not found")
            except Exception as e:
                logger.error(f"Error fetching performer ID for '{performer_name}': {e}")
                
        return performer_ids
    
    def _get_all_performers(self):
        "Fetch all performers from Stash for alias matching."
        # Try to fetch aliases if available
        try:
            # First try to discover schema to see what fields are available
            schema_query = (
                "query {"
                "  __schema {"
                "    types {"
                "      name"
                "      fields {"
                "        name"
                "      }"
                "    }"
                "  }"
                "}"
            )
            
            try:
                # Try to fetch schema - this might fail in some Stash versions
                schema_result = self.stash.call_GQL(schema_query)
                performer_type = None
                for t in schema_result.get('__schema', {}).get('types', []):
                    if t.get('name') == 'Performer' and t.get('fields'):
                        performer_type = t
                        break
                
                # If we found the Performer type in the schema, check available fields
                if performer_type:
                    field_names = [f.get('name') for f in performer_type.get('fields', []) if f.get('name')]
                    
                    if 'aliases' in field_names:
                        logger.debug("'aliases' field is available in schema")
                        alias_field = 'aliases'
                    elif 'alias_list' in field_names:
                        logger.debug("'alias_list' field is available in schema")
                        alias_field = 'alias_list'
                    else:
                        logger.debug("No alias fields found in schema")
                        alias_field = None
                    
                    # Construct query based on available fields
                    if alias_field:
                        query = (
                            f"query {{"
                            f"  findPerformers(filter: {{per_page: -1}}) {{"
                            f"    performers {{"
                            f"      id"
                            f"      name"
                            f"      {alias_field}"
                            f"    }}"
                            f"  }}"
                            f"}}"
                        )
                        result = self.stash.call_GQL(query)
                        performers = result.get('findPerformers', {}).get('performers', [])
                        
                        # Standardize the alias field name to 'aliases'
                        if alias_field == 'alias_list':
                            for performer in performers:
                                if 'alias_list' in performer:
                                    performer['aliases'] = performer.pop('alias_list')
                        
                        logger.debug(f"Successfully retrieved performers with {alias_field}")
                        return performers
                
            except Exception as e:
                logger.debug(f"Schema query failed, trying direct approaches: {e}")
            
            # Fall back to just names
            query = (
                "query {"
                "  findPerformers(filter: {per_page: -1}) {"
                "    performers {"
                "      id"
                "      name"
                "    }"
                "  }"
                "}"
            )
            result = self.stash.call_GQL(query)
            logger.warning("Could not retrieve alias information, only performer names available")
            return result.get('findPerformers', {}).get('performers', [])
            
        except Exception as e:
            logger.warning(f"Error fetching performers: {e}")
            return []
            
    def _get_all_studios(self):
        "Fetch all studios from Stash to check if detected studios exist."
        try:
            query = (
                "query {"
                "  findStudios(filter: {per_page: -1}) {"
                "    studios {"
                "      id"
                "      name"
                "    }"
                "  }"
                "}"
            )
            result = self.stash.call_GQL(query)
            return result.get('findStudios', {}).get('studios', [])
        except Exception as e:
            logger.warning(f"Error fetching studios: {e}")
            return []
            
    def _get_all_tags(self):
        "Fetch all tags from Stash for tag detection."
        try:
            query = (
                "query {"
                "  findTags(filter: {per_page: -1}) {"
                "    tags {"
                "      id"
                "      name"
                "      description"
                "    }"
                "  }"
                "}"
            )
            result = self.stash.call_GQL(query)
            tags = result.get('findTags', {}).get('tags', [])
            logger.debug(f"Fetched {len(tags)} tags from Stash")
            return tags
        except Exception as e:
            logger.warning(f"Error fetching tags: {e}")
            return []
            
    def _studio_exists_in_stash(self, studio_name, studios):
        "Check if a studio exists in Stash database."
        if not studio_name or not studios:
            return False
            
        normalized_name = studio_name.lower()
        for studio in studios:
            if studio.get('name', '').lower() == normalized_name:
                return True
        return False
    
    def _get_studio_id(self, studio_name, studios):
        "Get the ID of a studio by name."
        if not studio_name or not studios:
            return None
            
        normalized_name = studio_name.lower()
        for studio in studios:
            if studio.get('name', '').lower() == normalized_name:
                return studio.get('id')
        return None
        
    def _performer_exists_in_stash(self, performer_name, performers):
        "Check if a performer exists in Stash database."
        if not performer_name or not performers:
            return False
            
        normalized_name = performer_name.lower()
        for performer in performers:
            if performer.get('name', '').lower() == normalized_name:
                return True
        return False
        
    def _get_performer_id(self, performer_name, performers):
        "Get the ID of a performer by name."
        if not performer_name or not performers:
            return None
            
        normalized_name = performer_name.lower()
        for performer in performers:
            if performer.get('name', '').lower() == normalized_name:
                return performer.get('id')
        return None
    
    def _tag_exists_in_stash(self, tag_name, tags):
        "Check if a tag exists in Stash database."
        if not tag_name or not tags:
            return False
            
        normalized_name = tag_name.lower()
        for tag in tags:
            if tag.get('name', '').lower() == normalized_name:
                return True
        return False
        
    def _get_tag_id(self, tag_name, tags):
        "Get the ID of a tag by name."
        if not tag_name or not tags:
            return None
            
        normalized_name = tag_name.lower()
        for tag in tags:
            if tag.get('name', '').lower() == normalized_name:
                return tag.get('id')
        return None
        
    def _create_studio(self, studio_name):
        "Create a new studio in Stash."
        if not studio_name:
            return None
            
        try:
            mutation = (
                "mutation CreateStudio($input: StudioCreateInput!) {"
                "  studioCreate(input: $input) {"
                "    id"
                "  }"
                "}"
            )
            variables = {
                "input": {
                    "name": studio_name
                }
            }
            
            result = self.stash.call_GQL(mutation, variables)
            if result.get('studioCreate', {}).get('id'):
                logger.info(f"Created studio: '{studio_name}'")
                return result['studioCreate']['id']
            else:
                logger.error(f"Failed to create studio: '{studio_name}'")
                return None
        except Exception as e:
            logger.error(f"Error creating studio '{studio_name}': {e}")
            return None
    
    def _create_performer(self, performer_name):
        "Create a new performer in Stash."
        if not performer_name:
            return None
            
        try:
            # Split name into first and last name if it has a space
            name_parts = performer_name.split(' ', 1)
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            mutation = (
                "mutation CreatePerformer($input: PerformerCreateInput!) {"
                "  performerCreate(input: $input) {"
                "    id"
                "  }"
                "}"
            )
            variables = {
                "input": {
                    "name": performer_name,
                    "first_name": first_name,
                    "last_name": last_name
                }
            }
            
            result = self.stash.call_GQL(mutation, variables)
            if result.get('performerCreate', {}).get('id'):
                logger.info(f"Created performer: '{performer_name}'")
                return result['performerCreate']['id']
            else:
                logger.error(f"Failed to create performer: '{performer_name}'")
                return None
        except Exception as e:
            logger.error(f"Error creating performer '{performer_name}': {e}")
            return None
    
    def _create_tag(self, tag_name):
        "Create a new tag in Stash."
        if not tag_name:
            return None
            
        try:
            mutation = (
                "mutation CreateTag($input: TagCreateInput!) {"
                "  tagCreate(input: $input) {"
                "    id"
                "  }"
                "}"
            )
            variables = {
                "input": {
                    "name": tag_name
                }
            }
            
            result = self.stash.call_GQL(mutation, variables)
            if result.get('tagCreate', {}).get('id'):
                logger.info(f"Created tag: '{tag_name}'")
                return result['tagCreate']['id']
            else:
                logger.error(f"Failed to create tag: '{tag_name}'")
                return None
        except Exception as e:
            logger.error(f"Error creating tag '{tag_name}': {e}")
            return None
            
    def _update_scene(self, scene_id, updates):
        "Update a scene in Stash with the given changes."
        if not scene_id or not updates:
            return False
            
        try:
            mutation = (
                "mutation UpdateScene($input: SceneUpdateInput!) {"
                "  sceneUpdate(input: $input) {"
                "    id"
                "  }"
                "}"
            )
            
            variables = {
                "input": {
                    "id": scene_id,
                    **updates
                }
            }
            
            result = self.stash.call_GQL(mutation, variables)
            if result.get('sceneUpdate', {}).get('id'):
                return True
            else:
                logger.error(f"Failed to update scene: {scene_id}")
                return False
        except Exception as e:
            logger.error(f"Error updating scene {scene_id}: {e}")
            return False
            
    def _add_mark_tag_to_scene(self, scene_id, scene_tags, tag_name):
        "Add a marker tag to a scene to indicate it has been processed."
        if not scene_id or not tag_name:
            return False
            
        try:
            # Check if tag exists or create it
            tag_id = None
            all_tags = self._get_all_tags()
            
            # Look for existing tag
            for tag in all_tags:
                if tag.get('name', '').lower() == tag_name.lower():
                    tag_id = tag.get('id')
                    logger.debug(f"Found mark tag: '{tag_name}' (ID: {tag_id})")
                    break
                    
            # Create tag if it doesn't exist
            if not tag_id and self.create_missing:
                tag_id = self._create_tag(tag_name)
                if tag_id:
                    logger.info(f"Created mark tag: '{tag_name}'")
            
            # If we have a tag ID, add it to the scene
            if tag_id:
                # Get current tag IDs from the scene
                current_tag_ids = [t.get('id') for t in scene_tags if t.get('id')]
                
                # Check if tag is already applied
                if tag_id in current_tag_ids:
                    logger.debug(f"Mark tag '{tag_name}' already applied to scene {scene_id}")
                    return True
                
                # Add tag to the scene
                all_tag_ids = current_tag_ids + [tag_id]
                
                if self._update_scene(scene_id, {"tag_ids": all_tag_ids}):
                    logger.info(f"Added mark tag '{tag_name}' to scene {scene_id}")
                    return True
                else:
                    logger.error(f"Failed to add mark tag '{tag_name}' to scene {scene_id}")
                    return False
            else:
                logger.warning(f"Could not find or create mark tag: '{tag_name}'")
                return False
                
        except Exception as e:
            logger.error(f"Error adding mark tag to scene {scene_id}: {e}")
            return False
    
    def _extract_performer_aliases(self, path):
        "Extract potential performer names from filepath directories. Only extracts exact directory names with no special handling."
        logger.debug(f"Extracting potential performer aliases from '{os.path.basename(path)}'")
        aliases = []
        
        # Extract all directory names from the path
        path_parts = Path(path).parts
        logger.debug(f"Path parts: {path_parts}")
        
        # Skip first part (drive or root) and filename
        for part in path_parts[1:-1]:
            # Only consider non-empty parts that aren't common system directories
            if part and part not in ('data', 'media', 'videos', 'movies', 'scenes'):
                aliases.append(part)
                logger.debug(f"Extracted alias from directory name: '{part}'")
        
        if not aliases:
            logger.debug("No aliases extracted from path")
        else:
            logger.debug(f"Extracted aliases: {aliases}")
            
        return aliases
    
    def _match_alias_to_performer(self, alias, performers):
        "Attempt to match an alias to existing performers in two cases: 1) Exact match with performer name, 2) Exact match with both first and last name (if split_names is enabled)"
        logger.debug(f"Attempting to match alias '{alias}' to performers")
        
        # Skip short aliases
        if len(alias) < 3:
            logger.debug(f"Skipping alias '{alias}' - too short (< 3 chars)")
            return None
        
        # Normalize the alias
        normalized_alias = self._clean_name(alias).lower()
        logger.debug(f"Normalized alias: '{normalized_alias}'")
            
        # CASE 1: Check for exact matches in performer names
        for performer in performers:
            perf_name = performer.get('name', '').lower()
            if normalized_alias == perf_name:
                logger.debug(f"MATCH TYPE 1: Exact match with performer name '{performer.get('name')}'")
                return performer.get('name')
        
        # CASE 2: Check if alias contains exactly a performer's first and last name
        # Only do this if split_names is enabled
        if self.split_names and ' ' in normalized_alias:
            alias_parts = normalized_alias.split()
            if len(alias_parts) >= 2:  # Need at least 2 parts for first/last name
                logger.debug(f"Checking first/last name match with alias parts: {alias_parts}")
                
                for performer in performers:
                    perf_name = performer.get('name', '').lower()
                    perf_parts = perf_name.split()
                    
                    # Only compare if performer has at least first and last name
                    if len(perf_parts) >= 2:
                        # Check if both first and last name match exactly
                        if alias_parts[0] == perf_parts[0] and alias_parts[-1] == perf_parts[-1]:
                            logger.debug(f"MATCH TYPE 2: First and last name match with performer '{performer.get('name')}'")
                            return performer.get('name')
        
        logger.debug(f"No match found for alias '{alias}'")
        return None

    def generate_plan(self, plan_filename, plan_format='json', **kwargs):
        """Generate a plan file with proposed changes without applying them."""
        logger.info("Generating plan file...")
        
        # Store original settings
        original_apply_changes = self.apply_changes
        original_create_missing = self.create_missing
        original_dry_run = self.dry_run
        
        # Set to plan generation mode
        self.apply_changes = False
        self.create_missing = False
        self.dry_run = True
        
        try:
            # Initialize plan structure
            plan_data = {
                "metadata": {
                    "generated_at": datetime.datetime.now().isoformat(),
                    "script_version": "1.0",
                    "settings": {
                        "detect_studios": self.detect_studios,
                        "detect_performers": self.detect_performers,
                        "detect_tags": self.detect_tags,
                        "detect_details": self.detect_details,
                        "use_titles": self.use_titles,
                        "use_details": self.use_details,
                        "split_names": self.split_names
                    }
                },
                "scenes": []
            }
            
            # Collect changes for each scene
            self._collect_scene_changes(plan_data, is_plan_generation=True, **kwargs)
            
            # Write plan file
            self._write_plan_file(plan_filename, plan_data, plan_format)
            
            logger.info(f"Plan generated successfully: {plan_filename}")
            logger.info(f"Total scenes with changes: {len(plan_data['scenes'])}")
            
        finally:
            # Restore original settings
            self.apply_changes = original_apply_changes
            self.create_missing = original_create_missing
            self.dry_run = original_dry_run

    def apply_plan(self, plan_filename):
        """Apply changes from an existing plan file."""
        logger.info(f"Applying plan from: {plan_filename}")
        
        # Read and validate plan file
        plan_data = self._read_plan_file(plan_filename)
        if not plan_data:
            raise ValueError(f"Failed to read plan file: {plan_filename}")
        
        # Apply changes for each scene
        self._execute_plan_changes(plan_data)
        
        logger.info("Plan applied successfully")

    def _collect_scene_changes(self, plan_data, is_plan_generation=False, **kwargs):
        """Collect proposed changes for each scene."""
        # Get all scenes matching the filters
        try:
            scenes = self._get_scenes(**kwargs)
        except Exception as e:
            if self.dry_run:
                # In dry-run mode, provide cost estimate based on limit parameter if connection fails
                logger.warning(f"Could not connect to Stash for dry-run: {e}")
                logger.info("Providing cost estimate based on --limit parameter...")
                
                # Create mock scenes based on limit for cost estimation
                limit = kwargs.get('limit', 100)  # Default to 100 if no limit specified
                mock_scenes = []
                for i in range(limit):
                    mock_scenes.append({
                        'file_path': f'/mock/path/scene_{i+1}.mp4',
                        'title': f'Mock Scene {i+1}',
                        'details': 'Mock scene description for cost estimation',
                        'studio': {'name': 'Mock Studio'},
                    })
                
                if any([self.detect_studios, self.detect_performers, self.detect_tags, self.detect_details]):
                    logger.info("DRY RUN: Would process scenes with AI, but skipping API calls")
                    self._estimate_openai_cost(mock_scenes, batch_size=15)
                
                logger.info(f"Cost estimate based on {limit} scenes (actual scene count may vary)")
                return
            else:
                raise  # Re-raise the exception if not in dry-run mode
        
        if not scenes:
            logger.info("No scenes found matching the criteria")
            return
        
        logger.info(f"Found {len(scenes)} scenes to analyze")
        
        # Get existing metadata for comparison
        existing_studios = self._get_all_studios()
        existing_performers = self._get_all_performers()
        existing_tags = self._get_all_tags()
        
        # Pre-process scenes for AI analysis if needed
        ai_results = {}
        if any([self.detect_studios, self.detect_performers, self.detect_tags, self.detect_details]):
            if self.dry_run and not is_plan_generation:
                # True dry-run mode: just show cost estimate, don't run AI analysis
                logger.info("DRY RUN: Would process scenes with AI, but skipping API calls")
                
                # Provide cost estimate in dry run mode
                # Convert scenes to the format expected by the cost estimation
                batch_scenes = []
                for scene in scenes:
                    scene_path = scene.get('files', [{}])[0].get('path', '')
                    if scene_path:
                        batch_scenes.append({
                            'file_path': scene_path,
                            'title': scene.get('title', ''),
                            'details': scene.get('details', ''),
                            'studio': scene.get('studio', {}),
                        })
                
                if batch_scenes:
                    self._estimate_openai_cost(batch_scenes, batch_size=15)
            else:
                # Normal mode OR plan generation mode: run AI analysis
                if is_plan_generation:
                    logger.info("Plan generation: Running AI analysis to collect proposed changes")
                ai_results = self._run_ai_analysis(scenes)
        
        # Analyze each scene and collect changes
        for i, scene in enumerate(scenes, 1):
            scene_path = scene.get('files', [{}])[0].get('path', '')
            scene_id = scene.get('id')
            
            logger.info(f"[ANALYZING] Scene: [{i}/{len(scenes)}] ID: {scene_id}")
            
            # Get current scene metadata
            current_studio = scene.get('studio', {}).get('name') if scene.get('studio') else None
            current_performers = [p.get('name') for p in scene.get('performers', [])]
            current_tags = [t.get('name') for t in scene.get('tags', [])]
            current_details = scene.get('details', '')
            
            # Get AI detection results
            detected_studio = None
            detected_performers = []
            detected_tags = []
            detected_details = None
            
            if scene_path in ai_results:
                detected_studio = ai_results[scene_path].get('studio') if self.detect_studios else None
                detected_performers = ai_results[scene_path].get('performers', []) if self.detect_performers else []
                detected_tags = ai_results[scene_path].get('tags', []) if self.detect_tags else []
                detected_details = ai_results[scene_path].get('details') if self.detect_details else None
            
            # Collect proposed changes
            proposed_changes = {}
            
            # Studio changes
            if self.detect_studios and detected_studio and detected_studio != current_studio:
                proposed_changes['studio'] = {
                    'action': 'set',
                    'value': detected_studio,
                    'confidence': 0.9  # Could be enhanced with actual confidence scores
                }
            
            # Performer changes
            if self.detect_performers and detected_performers:
                new_performers = [p for p in detected_performers if p not in current_performers]
                if new_performers:
                    proposed_changes['performers'] = {
                        'action': 'add',
                        'values': new_performers
                    }
            
            # Tag changes
            if self.detect_tags and detected_tags:
                new_tags = [t for t in detected_tags if t not in current_tags]
                if new_tags:
                    proposed_changes['tags'] = {
                        'action': 'add',
                        'values': new_tags
                    }
            
            # Details changes
            if self.detect_details and detected_details and detected_details != current_details:
                proposed_changes['details'] = {
                    'action': 'update',
                    'value': detected_details
                }
            
            # Only add scenes with changes to the plan
            if proposed_changes:
                scene_data = {
                    'scene_id': scene_id,
                    'current_state': {
                        'title': scene.get('title', ''),
                        'path': scene_path,
                        'studio': current_studio,
                        'performers': current_performers,
                        'tags': current_tags,
                        'details': current_details
                    },
                    'proposed_changes': proposed_changes
                }
                plan_data['scenes'].append(scene_data)

    def _write_plan_file(self, filename, plan_data, format='json'):
        """Write plan data to file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                if format == 'json':
                    json.dump(plan_data, f, indent=2, ensure_ascii=False)
                elif format == 'yaml':
                    import yaml
                    yaml.dump(plan_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    raise ValueError(f"Unsupported plan format: {format}")
            
            logger.info(f"Plan file written: {filename}")
        except Exception as e:
            logger.error(f"Failed to write plan file: {e}")
            raise

    def _read_plan_file(self, filename):
        """Read and validate plan file."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    import yaml
                    plan_data = yaml.safe_load(f)
                else:
                    plan_data = json.load(f)
            
            # Basic validation
            if not isinstance(plan_data, dict):
                raise ValueError("Plan file must contain a JSON object")
            
            if 'scenes' not in plan_data:
                raise ValueError("Plan file must contain 'scenes' array")
            
            if not isinstance(plan_data['scenes'], list):
                raise ValueError("'scenes' must be an array")
            
            logger.info(f"Plan file loaded: {filename}")
            logger.info(f"Scenes in plan: {len(plan_data['scenes'])}")
            
            return plan_data
            
        except Exception as e:
            logger.error(f"Failed to read plan file: {e}")
            return None

    def _execute_plan_changes(self, plan_data):
        """Execute all changes from the plan."""
        scenes = plan_data.get('scenes', [])
        
        if not scenes:
            logger.info("No scenes to process in plan")
            return
        
        logger.info(f"Processing {len(scenes)} scenes from plan")
        
        # Get existing metadata for lookups
        existing_studios = self._get_all_studios()
        existing_performers = self._get_all_performers()
        existing_tags = self._get_all_tags()
        
        success_count = 0
        error_count = 0
        
        for i, scene_data in enumerate(scenes, 1):
            scene_id = scene_data.get('scene_id')
            proposed_changes = scene_data.get('proposed_changes', {})
            
            logger.info(f"[APPLYING] Scene: [{i}/{len(scenes)}] ID: {scene_id}")
            
            try:
                # Apply each type of change
                updates = {}
                
                # Studio changes
                if 'studio' in proposed_changes:
                    studio_change = proposed_changes['studio']
                    if studio_change.get('action') == 'set':
                        studio_name = studio_change.get('value')
                        if studio_name:
                            studio_id = self._get_studio_id(studio_name, existing_studios)
                            if not studio_id and self.create_missing:
                                studio_id = self._create_studio(studio_name)
                                if studio_id:
                                    # Refresh studios list
                                    existing_studios = self._get_all_studios()
                            
                            if studio_id:
                                updates['studio_id'] = studio_id
                                logger.info(f"  Setting studio: {studio_name}")
                
                # Performer changes
                if 'performers' in proposed_changes:
                    performer_change = proposed_changes['performers']
                    if performer_change.get('action') == 'add':
                        new_performers = performer_change.get('values', [])
                        current_performers = scene_data.get('current_state', {}).get('performers', [])
                        
                        # Get IDs for existing and new performers
                        performer_ids = []
                        
                        # Add current performers
                        for perf_name in current_performers:
                            perf_id = self._get_performer_id(perf_name, existing_performers)
                            if perf_id:
                                performer_ids.append(perf_id)
                        
                        # Add new performers
                        for perf_name in new_performers:
                            perf_id = self._get_performer_id(perf_name, existing_performers)
                            if not perf_id and self.create_missing:
                                perf_id = self._create_performer(perf_name)
                                if perf_id:
                                    # Refresh performers list
                                    existing_performers = self._get_all_performers()
                            
                            if perf_id:
                                performer_ids.append(perf_id)
                                logger.info(f"  Adding performer: {perf_name}")
                        
                        if performer_ids:
                            updates['performer_ids'] = list(set(performer_ids))  # Remove duplicates
                
                # Tag changes
                if 'tags' in proposed_changes:
                    tag_change = proposed_changes['tags']
                    if tag_change.get('action') == 'add':
                        new_tags = tag_change.get('values', [])
                        current_tags = scene_data.get('current_state', {}).get('tags', [])
                        
                        # Get IDs for existing and new tags
                        tag_ids = []
                        
                        # Add current tags
                        for tag_name in current_tags:
                            tag_id = self._get_tag_id(tag_name, existing_tags)
                            if tag_id:
                                tag_ids.append(tag_id)
                        
                        # Add new tags
                        for tag_name in new_tags:
                            tag_id = self._get_tag_id(tag_name, existing_tags)
                            if not tag_id and self.create_missing:
                                tag_id = self._create_tag(tag_name)
                                if tag_id:
                                    # Refresh tags list
                                    existing_tags = self._get_all_tags()
                            
                            if tag_id:
                                tag_ids.append(tag_id)
                                logger.info(f"  Adding tag: {tag_name}")
                        
                        if tag_ids:
                            updates['tag_ids'] = list(set(tag_ids))  # Remove duplicates
                
                # Details changes
                if 'details' in proposed_changes:
                    details_change = proposed_changes['details']
                    if details_change.get('action') == 'update':
                        new_details = details_change.get('value')
                        if new_details:
                            updates['details'] = new_details
                            logger.info(f"  Updating details")
                
                # Apply all updates to the scene
                if updates:
                    if not self.dry_run:
                        self._update_scene(scene_id, updates)
                        success_count += 1
                    else:
                        logger.info(f"  [DRY RUN] Would apply updates: {list(updates.keys())}")
                        success_count += 1
                else:
                    logger.info(f"  No changes to apply")
                    
            except Exception as e:
                logger.error(f"  Failed to apply changes: {e}")
                error_count += 1
        
        logger.info(f"Plan execution completed: {success_count} successful, {error_count} errors")

    def _get_scenes(self, verbose=False, batch_size=15, limit=None, scene_id=None, 
                   include_tags=None, exclude_tags=None, include_performers=None, 
                   title_filter=None, organized=None, path_filter=None,
                   created_after=None, created_before=None, date_after=None, date_before=None):
        """Get scenes matching the specified filters."""
        
        # If a specific scene_id is provided, only get that scene
        if scene_id:
            query = (
                "query FindScene($id: ID!) {"
                "  findScene(id: $id) {"
                "    id"
                "    title"
                "    details"
                "    files {"
                "      path"
                "    }"
                "    studio {"
                "      name"
                "    }"
                "    performers {"
                "      name"
                "    }"
                "    tags {"
                "      name"
                "    }"
                "  }"
                "}"
            )
            logger.debug(f"Fetching scene with ID {scene_id}")
            result = self.stash.call_GQL(query, {'id': scene_id})
            scene = result.get('findScene')
            
            if not scene:
                logger.error(f"Scene with ID {scene_id} not found")
                return []
                
            return [scene]
        else:
            # Get all scenes with proper pagination
            page = 1
            per_page = 100  # Fetch 100 scenes at a time
            scenes = []
            total_count = 0
            
            logger.debug("Fetching scenes with pagination and filters")
            
            # Build the scene filter based on parameters
            scene_filter = {}
            filter_conditions = []
            
            # Tag filters
            if include_tags:
                include_tag_ids = self._get_tag_ids(include_tags)
                if include_tag_ids:
                    scene_filter['tags'] = {'value': include_tag_ids, 'modifier': 'INCLUDES_ALL'}
                    filter_conditions.append(f"including tags: {', '.join(include_tags)}")
                    
            if exclude_tags:
                exclude_tag_ids = self._get_tag_ids(exclude_tags)
                if exclude_tag_ids:
                    if 'tags' not in scene_filter:
                        scene_filter['tags'] = {}
                    scene_filter['tags']['excludes'] = exclude_tag_ids
                    filter_conditions.append(f"excluding tags: {', '.join(exclude_tags)}")
            
            # Performer filter
            if include_performers:
                performer_ids = self._get_performer_ids(include_performers)
                if performer_ids:
                    scene_filter['performers'] = {'value': performer_ids, 'modifier': 'INCLUDES_ALL'}
                    filter_conditions.append(f"including performers: {', '.join(include_performers)}")
            
            # Title filter
            if title_filter:
                scene_filter['title'] = {'value': title_filter, 'modifier': 'INCLUDES'}
                filter_conditions.append(f"title contains: {title_filter}")
            
            # Path filter
            if path_filter:
                scene_filter['path'] = {'value': path_filter, 'modifier': 'INCLUDES'}
                filter_conditions.append(f"path contains: {path_filter}")
            
            # Organized flag
            if organized is not None:
                scene_filter['organized'] = organized
                filter_conditions.append(f"organized: {'yes' if organized else 'no'}")
            
            # Created date filters
            created_after_date = self._parse_date_filter(created_after)
            created_before_date = self._parse_date_filter(created_before)
            
            if created_after_date:
                scene_filter['created_at'] = {'value': created_after_date.strftime('%Y-%m-%dT%H:%M:%S%z'), 'modifier': 'GREATER_THAN'}
                filter_conditions.append(f"created after: {created_after}")
                
            if created_before_date:
                scene_filter['created_at'] = {'value': created_before_date.strftime('%Y-%m-%dT%H:%M:%S%z'), 'modifier': 'LESS_THAN'}
                filter_conditions.append(f"created before: {created_before}")
            
            # Scene date filters
            date_after_date = self._parse_date_filter(date_after)
            date_before_date = self._parse_date_filter(date_before)
            
            if date_after_date:
                scene_filter['date'] = {'value': date_after_date.strftime('%Y-%m-%d'), 'modifier': 'GREATER_THAN'}
                filter_conditions.append(f"scene date after: {date_after}")
                
            if date_before_date:
                scene_filter['date'] = {'value': date_before_date.strftime('%Y-%m-%d'), 'modifier': 'LESS_THAN'}
                filter_conditions.append(f"scene date before: {date_before}")
            
            if filter_conditions:
                logger.info(f"Applied filters: {'; '.join(filter_conditions)}")
            
            # Fetch scenes with pagination
            while True:
                query = (
                    "query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType) {"
                    "  findScenes(filter: $filter, scene_filter: $scene_filter) {"
                    "    count"
                    "    scenes {"
                    "      id"
                    "      title"
                    "      details"
                    "      files {"
                    "        path"
                    "      }"
                    "      studio {"
                    "        name"
                    "      }"
                    "      performers {"
                    "        name"
                    "      }"
                    "      tags {"
                    "        name"
                    "      }"
                    "    }"
                    "  }"
                    "}"
                )
                
                variables = {
                    'filter': {
                        'page': page,
                        'per_page': per_page,
                        'sort': 'id',
                        'direction': 'ASC'
                    },
                    'scene_filter': scene_filter
                }
                
                logger.debug(f"Fetching page {page} with {per_page} scenes per page")
                result = self.stash.call_GQL(query, variables)
                
                if not result or 'findScenes' not in result:
                    logger.error("Failed to fetch scenes from Stash")
                    break
                
                page_scenes = result['findScenes']['scenes']
                if not page_scenes:
                    logger.debug("No more scenes found")
                    break
                
                scenes.extend(page_scenes)
                total_count = result['findScenes']['count']
                
                logger.debug(f"Fetched {len(page_scenes)} scenes, total so far: {len(scenes)}")
                
                # Apply limit if specified
                if limit and len(scenes) >= limit:
                    scenes = scenes[:limit]
                    logger.info(f"Limiting to {limit} scenes as requested")
                    break
                
                # Check if we've fetched all scenes
                if len(page_scenes) < per_page:
                    logger.debug("Reached end of scenes")
                    break
                
                page += 1
            
            logger.info(f"Total scenes fetched: {len(scenes)}")
            if total_count > 0:
                logger.info(f"Total scenes matching filters: {total_count}")
            
            return scenes

    def _run_ai_analysis(self, scenes):
        """Run AI analysis on scenes and return results using batch processing."""
        ai_results = {}
        
        if not self.openai_client:
            logger.warning("OpenAI client not available - skipping AI analysis")
            return ai_results
        
        logger.info(f"Running AI analysis on {len(scenes)} scenes using batch processing")
        
        # Convert scenes to the format expected by _batch_detect_with_ai
        batch_scenes = []
        for scene in scenes:
            scene_path = scene.get('files', [{}])[0].get('path', '')
            if scene_path:
                # Create a scene record compatible with batch processing
                batch_scene = {
                    'file_path': scene_path,
                    'title': scene.get('title', ''),
                    'details': scene.get('details', ''),
                    'studio': scene.get('studio', {}),
                    'scene_data': scene  # Keep original scene data for reference
                }
                batch_scenes.append(batch_scene)
        
        if not batch_scenes:
            logger.warning("No valid scenes found for AI analysis")
            return ai_results
        
        # Use existing batch processing with default batch size
        logger.info(f"Processing {len(batch_scenes)} scenes using batch AI detection")
        ai_results = self._batch_detect_with_ai(batch_scenes, batch_size=15)
        
        logger.info(f"AI analysis completed for {len(ai_results)} scenes")
        return ai_results



def _test_env_vars(args):
    """
    Test function to verify environment variable parsing.
    This is called when STASHSCRIPTS_DEBUG_ENV=1 is set to display all parsed arguments.
    """
    print("\n--- Environment Variable Test ---")
    print("Arguments parsed from environment variables and command line:")
    
    # Get all attributes from args
    arg_dict = vars(args)
    for key, value in arg_dict.items():
        print(f"  {key}: {value}")
    
    print("-------------------------------\n")
    
    # Return True to indicate test was run
    return True


def main():
    parser = argparse.ArgumentParser(description='Analyze Stash scenes for studio and performer detection')
    
    # Environment variable prefix for all options
    env_prefix = "STASHSCRIPTS_"
    
    # Create a mapping of CLI arguments to environment variables
    env_mappings = {
        'url': f'{env_prefix}URL',
        'api_key': f'{env_prefix}API_KEY',
        'log_level': f'{env_prefix}LOG_LEVEL',
        'use_titles': f'{env_prefix}USE_TITLES',
        'use_details': f'{env_prefix}USE_DETAILS',
        'use_studio': f'{env_prefix}USE_STUDIO',
        'detect_performers': f'{env_prefix}DETECT_PERFORMERS',
        'detect_studios': f'{env_prefix}DETECT_STUDIOS',
        'detect_tags': f'{env_prefix}DETECT_TAGS',
        'detect_details': f'{env_prefix}DETECT_DETAILS',
        'openai_api_key': 'OPENAI_API_KEY',  # Keep original env var for compatibility
        'openai_model': f'{env_prefix}OPENAI_MODEL',
        'openai_base_url': f'{env_prefix}OPENAI_BASE_URL',
        'batch_size': f'{env_prefix}BATCH_SIZE',
        'limit': f'{env_prefix}LIMIT',
        'split_names': f'{env_prefix}SPLIT_NAMES',
        'dry_run': f'{env_prefix}DRY_RUN',
        'show_prompts': f'{env_prefix}SHOW_PROMPTS',
        'colorize': f'{env_prefix}COLORIZE',
        'apply_changes': f'{env_prefix}APPLY_CHANGES',
        'create_missing': f'{env_prefix}CREATE_MISSING',
        'mark_tag': f'{env_prefix}MARK_TAG',
        'scene_id': f'{env_prefix}SCENE_ID',
        'include_tags': f'{env_prefix}INCLUDE_TAGS',  # Added for list arguments
        'exclude_tags': f'{env_prefix}EXCLUDE_TAGS',  # Added for list arguments
        'performers': f'{env_prefix}PERFORMERS',      # Added for list arguments
        'title': f'{env_prefix}TITLE',
        'path': f'{env_prefix}PATH',
        'organized': f'{env_prefix}ORGANIZED',
        'unorganized': f'{env_prefix}UNORGANIZED',
        'created_after': f'{env_prefix}CREATED_AFTER',
        'created_before': f'{env_prefix}CREATED_BEFORE',
        'date_after': f'{env_prefix}DATE_AFTER',
        'date_before': f'{env_prefix}DATE_BEFORE',
    }
    
    # Helper function to get default values from environment variables
    def get_env_default(arg_name, default=None, is_bool=False, is_int=False):
        env_var = env_mappings.get(arg_name)
        if env_var and env_var in os.environ:
            value = os.environ[env_var]
            if is_bool:
                # Convert string to boolean: "true", "yes", "1" are True
                return value.lower() in ("true", "yes", "1", "y")
            elif is_int:
                try:
                    return int(value)
                except ValueError:
                    logger.warning(f"Invalid integer value '{value}' for environment variable {env_var}. Using default.")
                    return default
            return value
        return default
    
    # Add arguments with environment variable defaults
    parser.add_argument('--url', default=get_env_default('url', 'http://localhost:9999'), 
                       help='Stash server URL (env: STASHSCRIPTS_URL)')
    parser.add_argument('--api-key', default=get_env_default('api_key'), 
                       help='Stash API key (env: STASHSCRIPTS_API_KEY)')
    
    # Logging options
    verbosity_group = parser.add_argument_group('Logging Options')
    verbosity_group.add_argument('--log-level', '-l', 
                               choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                               default=get_env_default('log_level', 'WARNING'),
                               help='Set the logging level (env: STASHSCRIPTS_LOG_LEVEL)')
    
    # AI options
    parser.add_argument('--use-titles', action='store_true', 
                       default=get_env_default('use_titles', False, is_bool=True),
                       help='Include scene titles in AI analysis (env: STASHSCRIPTS_USE_TITLES)')
    parser.add_argument('--use-details', action='store_true', 
                       default=get_env_default('use_details', False, is_bool=True),
                       help='Include scene descriptions in AI analysis (env: STASHSCRIPTS_USE_DETAILS)')
    parser.add_argument('--use-studio', action='store_true', 
                       default=get_env_default('use_studio', False, is_bool=True),
                       help='Include current studio name in AI analysis for context (env: STASHSCRIPTS_USE_STUDIO)')
    
    # Detection features
    feature_group = parser.add_argument_group('Detection Features')
    feature_group.add_argument('--detect-performers', action='store_true', 
                             default=get_env_default('detect_performers', False, is_bool=True),
                             help='Detect performers using AI (env: STASHSCRIPTS_DETECT_PERFORMERS)')
    feature_group.add_argument('--detect-studios', action='store_true', 
                             default=get_env_default('detect_studios', False, is_bool=True),
                             help='Detect studios using AI (env: STASHSCRIPTS_DETECT_STUDIOS)')
    feature_group.add_argument('--detect-tags', action='store_true', 
                             default=get_env_default('detect_tags', False, is_bool=True),
                             help='Detect matching tags from your Stash tags list using AI (env: STASHSCRIPTS_DETECT_TAGS)')
    feature_group.add_argument('--detect-details', action='store_true', 
                             default=get_env_default('detect_details', False, is_bool=True),
                             help='Detect and clean HTML from scene descriptions (env: STASHSCRIPTS_DETECT_DETAILS)')
    
    parser.add_argument('--openai-api-key', default=get_env_default('openai_api_key'),
                       help='OpenAI API key (env: OPENAI_API_KEY)')
    parser.add_argument('--openai-model', default=get_env_default('openai_model'),
                       help='OpenAI model to use (env: STASHSCRIPTS_OPENAI_MODEL)')
    parser.add_argument('--openai-base-url', default=get_env_default('openai_base_url'),
                       help='Override the OpenAI API endpoint (env: STASHSCRIPTS_OPENAI_BASE_URL)')
    parser.add_argument('--batch-size', type=int, 
                       default=get_env_default('batch_size', 15, is_int=True),
                       help='Number of scenes to process in each AI batch (env: STASHSCRIPTS_BATCH_SIZE)')
    
    # Analysis options  
    parser.add_argument('--limit', type=int, 
                       default=get_env_default('limit', 15, is_int=True),
                       help='Limit the number of scenes to analyze (env: STASHSCRIPTS_LIMIT)')
    parser.add_argument('--split-names', action='store_true', 
                       default=get_env_default('split_names', False, is_bool=True),
                       help='Try to split directory names into performer names (env: STASHSCRIPTS_SPLIT_NAMES)')
    parser.add_argument('--dry-run', action='store_true', 
                       default=get_env_default('dry_run', False, is_bool=True),
                       help='Only log which scenes would be analyzed (env: STASHSCRIPTS_DRY_RUN)')
    parser.add_argument('--show-prompts', action='store_true', 
                       default=get_env_default('show_prompts', False, is_bool=True),
                       help='Output the full OpenAI prompts to the console (env: STASHSCRIPTS_SHOW_PROMPTS)')
    parser.add_argument('--colorize', action='store_true', 
                       default=get_env_default('colorize', False, is_bool=True),
                       help='Use colors in terminal output (env: STASHSCRIPTS_COLORIZE)')
    
    # Update options
    update_group = parser.add_argument_group('Update Options')
    update_group.add_argument('--apply-changes', action='store_true', 
                            default=get_env_default('apply_changes', False, is_bool=True),
                            help='Apply detected changes to scenes (env: STASHSCRIPTS_APPLY_CHANGES)')
    update_group.add_argument('--create-missing', action='store_true', 
                            default=get_env_default('create_missing', False, is_bool=True),
                            help='Create missing studios, performers, and tags (env: STASHSCRIPTS_CREATE_MISSING)')
    update_group.add_argument('--mark-tag', metavar='TAG', 
                            default=get_env_default('mark_tag'),
                            help='Tag to add to scenes after processing (env: STASHSCRIPTS_MARK_TAG)')
    
    # Plan options
    plan_group = parser.add_argument_group('Plan Options', 
                                          description='Generate and apply change plans for review-before-apply workflow')
    plan_group.add_argument('--generate-plan', metavar='FILENAME',
                           help='Generate a plan file with proposed changes without applying them. '
                                'This allows you to review all changes before applying them.')
    plan_group.add_argument('--apply-plan', metavar='FILENAME',
                           help='Apply changes from an existing plan file. '
                                'Use this after reviewing a plan generated with --generate-plan.')
    plan_group.add_argument('--plan-format', choices=['json', 'yaml'], default='json',
                           help='Plan file format (default: json). YAML requires PyYAML package.')
    
    # Scene filtering options
    filter_group = parser.add_argument_group('Scene Filtering Options')
    
    # For scene_id, we need to handle type conversion in the parser
    scene_id_env = get_env_default('scene_id', None, is_int=True)
    filter_group.add_argument('--scene-id', type=int, default=scene_id_env,
                            help='Analyze only a single scene with the given ID (env: STASHSCRIPTS_SCENE_ID)')
    
    # For list arguments, we need special handling with environment variables
    # We'll read environment variables first, then allow CLI arguments to override/append
    include_tags_env = []
    if os.environ.get(env_mappings['include_tags']):
        include_tags_env = os.environ[env_mappings['include_tags']].split(',')
    
    exclude_tags_env = []
    if os.environ.get(env_mappings['exclude_tags']):
        exclude_tags_env = os.environ[env_mappings['exclude_tags']].split(',')
    
    performers_env = []
    if os.environ.get(env_mappings['performers']):
        performers_env = os.environ[env_mappings['performers']].split(',')
    
    # Add arguments without default values to allow CLI flags to append to env vars
    filter_group.add_argument('--include-tag', action='append', dest='include_tags', 
                            help='Include scenes with this tag (env: STASHSCRIPTS_INCLUDE_TAGS comma-separated)')
    filter_group.add_argument('--exclude-tag', action='append', dest='exclude_tags', 
                            help='Exclude scenes with this tag (env: STASHSCRIPTS_EXCLUDE_TAGS comma-separated)')
    filter_group.add_argument('--performer', action='append', dest='performers', 
                            help='Include scenes with this performer (env: STASHSCRIPTS_PERFORMERS comma-separated)')
    
    filter_group.add_argument('--title', default=get_env_default('title'),
                            help='Filter scenes by title (env: STASHSCRIPTS_TITLE)')
    filter_group.add_argument('--path', default=get_env_default('path'),
                            help='Filter scenes by file path (env: STASHSCRIPTS_PATH)')
    filter_group.add_argument('--organized', action='store_true', 
                            default=get_env_default('organized', False, is_bool=True),
                            help='Include only organized scenes (env: STASHSCRIPTS_ORGANIZED)')
    filter_group.add_argument('--unorganized', action='store_true', 
                            default=get_env_default('unorganized', False, is_bool=True),
                            help='Include only unorganized scenes (env: STASHSCRIPTS_UNORGANIZED)')
    
    # Date filtering options
    date_group = parser.add_argument_group('Date Filtering Options')
    date_group.add_argument('--created-after', default=get_env_default('created_after'),
                          help='Filter scenes created after this date (env: STASHSCRIPTS_CREATED_AFTER)')
    date_group.add_argument('--created-before', default=get_env_default('created_before'),
                          help='Filter scenes created before this date (env: STASHSCRIPTS_CREATED_BEFORE)')
    date_group.add_argument('--date-after', default=get_env_default('date_after'),
                          help='Filter scenes with date after this date (env: STASHSCRIPTS_DATE_AFTER)')
    date_group.add_argument('--date-before', default=get_env_default('date_before'),
                          help='Filter scenes with date before this date (env: STASHSCRIPTS_DATE_BEFORE)')
    
    args = parser.parse_args()
    
    # Handle list arguments - combine env vars with CLI flags
    # CLI flags take priority over environment variables 
    # If the same value is specified in both, it will only appear once
    
    # For include_tags
    if include_tags_env:
        if args.include_tags:
            # CLI flags were provided - combine with env vars
            # Use a set to remove duplicates
            combined_tags = set(include_tags_env + args.include_tags)
            args.include_tags = list(combined_tags)
        else:
            # No CLI flags, use env vars only
            args.include_tags = include_tags_env
    
    # For exclude_tags  
    if exclude_tags_env:
        if args.exclude_tags:
            # CLI flags were provided - combine with env vars
            # Use a set to remove duplicates
            combined_tags = set(exclude_tags_env + args.exclude_tags)
            args.exclude_tags = list(combined_tags)
        else:
            # No CLI flags, use env vars only
            args.exclude_tags = exclude_tags_env
    
    # For performers
    if performers_env:
        if args.performers:
            # CLI flags were provided - combine with env vars
            # Use a set to remove duplicates
            combined_performers = set(performers_env + args.performers)
            args.performers = list(combined_performers)
        else:
            # No CLI flags, use env vars only
            args.performers = performers_env
    
    # Run environment variable test if debug env var is set
    if os.environ.get(f'{env_prefix}DEBUG_ENV') in ('1', 'true', 'yes', 'y'):
        _test_env_vars(args)
    
    # Check if we need OpenAI API (performers, studios, or tags detection)
    needs_openai = args.detect_performers or args.detect_studios or args.detect_tags
    
    # Validate OpenAI API key, but only if we need it
    if needs_openai and not args.openai_api_key:
        openai_key = os.environ.get('OPENAI_API_KEY')
        if not openai_key:
            print("ERROR: --openai-api-key is required for AI detection (or set OPENAI_API_KEY environment variable)")
            print("If you only want to use --detect-details without AI, don't enable the AI detection flags")
            return 1
        args.openai_api_key = openai_key
    
    # Check for conflicting arguments
    if args.scene_id and args.limit != 15:  # If limit wasn't explicitly changed
        print("Warning: --limit is ignored when --scene-id is specified")
    
    # Convert limit of 0 to None (process all scenes)
    limit = args.limit if args.limit > 0 else None
    
    # Set log level based on the log-level argument
    log_level = getattr(logging, args.log_level)
    
    # Configure our logger here, once, for the entire application
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    
    # Remove any existing handlers
    logger.handlers = [] 
    
    # Add a single handler
    logger.addHandler(handler)
    
    # Set the logger level based on the log_level parameter
    logger.setLevel(log_level)
    
    # No need to check for conflicting arguments since all options now work without --use-ai
        
    # Dry run or local-only detection doesn't actually need an API key
    if (args.dry_run or not needs_openai) and not args.openai_api_key:
        if args.dry_run:
            logger.info("Dry run mode doesn't require an OpenAI API key")
        if not needs_openai:
            logger.info("No AI-backed detections enabled, OpenAI API key not required")
        args.openai_api_key = "not-needed"
    
    try:
        # Use detect flags directly from args
        detect_performers = args.detect_performers
        detect_studios = args.detect_studios
        
        # Check that --create-missing is only used with --apply-changes
        if args.create_missing and not args.apply_changes:
            logger.warning("--create-missing requires --apply-changes to be effective. Missing entities will be created but not applied to scenes.")
            
        # Check that --mark-tag is only used with --apply-changes
        if args.mark_tag and not args.apply_changes:
            logger.warning("--mark-tag requires --apply-changes to be effective. Tag will be ignored.")
        
        analyzer = SceneAnalyzer(
            args.url, 
            args.api_key, 
            args.openai_api_key,
            args.openai_model,  # Pass the OpenAI model parameter
            args.openai_base_url,  # Pass the OpenAI base URL parameter
            args.use_titles,
            args.use_details,
            args.use_studio,
            detect_performers,
            detect_studios,
            args.detect_tags,
            args.detect_details,  # Pass the detect_details parameter
            args.split_names,
            args.apply_changes,
            args.create_missing,
            args.mark_tag if args.apply_changes else None,  # Only use mark_tag if apply_changes is enabled
            args.dry_run,
            log_level,
            args.show_prompts,
            args.colorize
        )
        
        # Handle plan modes
        if args.apply_plan:
            logger.info(f"Applying plan from: {args.apply_plan}")
            analyzer.apply_plan(args.apply_plan)
            return 0
        
        # Handle organized/unorganized flag
        organized = None
        if args.organized and not args.unorganized:
            organized = True
        elif args.unorganized and not args.organized:
            organized = False
        elif args.organized and args.unorganized:
            logger.warning("Both --organized and --unorganized flags are set. Ignoring both.")
        
        # Pass verbosity setting based on log level
        is_verbose = log_level <= logging.INFO
        # Run analysis with optional plan generation
        if args.generate_plan:
            logger.info(f"Generating plan to: {args.generate_plan}")
            analyzer.generate_plan(
                plan_filename=args.generate_plan,
                plan_format=args.plan_format,
                verbose=is_verbose, 
                batch_size=args.batch_size, 
                limit=limit, 
                scene_id=args.scene_id,
                include_tags=args.include_tags,
                exclude_tags=args.exclude_tags,
                include_performers=args.performers,
                title_filter=args.title,
                organized=organized,
                path_filter=args.path,
                created_after=args.created_after,
                created_before=args.created_before,
                date_after=args.date_after,
                date_before=args.date_before
            )
        else:
            analyzer.analyze_scenes(
                verbose=is_verbose, 
                batch_size=args.batch_size, 
                limit=limit, 
                scene_id=args.scene_id,
                include_tags=args.include_tags,
                exclude_tags=args.exclude_tags,
                include_performers=args.performers,
                title_filter=args.title,
                organized=organized,
                path_filter=args.path,
                created_after=args.created_after,
                created_before=args.created_before,
                date_after=args.date_after,
                date_before=args.date_before
            )
    except Exception as e:
        logger.error(f"{e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main())