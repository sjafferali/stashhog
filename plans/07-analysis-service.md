# Task 07: Analysis Service Implementation

## Current State
- Sync functionality can import scenes from Stash
- Legacy analyze_scenes.py contains analysis logic
- No integration with OpenAI or analysis features
- No plan generation capability

## Objective
Port and enhance the analysis logic from the legacy script into a modern service architecture, adding plan generation and management capabilities.

## Requirements

### Core Analysis Service

1. **app/services/analysis_service.py** - Main analysis orchestrator:
   ```python
   class AnalysisService:
       def __init__(
           self,
           openai_client: OpenAI,
           stash_service: StashService,
           settings: Settings
       ):
           # Initialize with dependencies
           
       async def analyze_scenes(
           self,
           scene_ids: Optional[List[str]] = None,
           filters: Optional[Dict] = None,
           options: AnalysisOptions = None,
           job_id: Optional[str] = None
       ) -> AnalysisPlan:
           """Analyze scenes and generate plan"""
           
       async def analyze_single_scene(
           self,
           scene: Scene,
           options: AnalysisOptions
       ) -> List[ProposedChange]:
           """Analyze one scene"""
   ```

### Analysis Options

2. **app/services/analysis/models.py** - Analysis models:
   ```python
   @dataclass
   class AnalysisOptions:
       detect_performers: bool = False
       detect_studios: bool = False
       detect_tags: bool = False
       detect_details: bool = False
       use_ai: bool = True
       create_missing: bool = False
       split_performer_names: bool = False
       confidence_threshold: float = 0.7
       
   @dataclass
   class ProposedChange:
       field: str  # "performers", "studio", "tags", "details"
       action: str  # "add", "remove", "update", "set"
       current_value: Any
       proposed_value: Any
       confidence: float
       reason: Optional[str]
   ```

### Detection Modules

3. **app/services/analysis/studio_detector.py** - Studio detection:
   ```python
   class StudioDetector:
       def __init__(self):
           # Initialize with patterns from legacy script
           self.patterns = self._load_patterns()
           
       async def detect_from_path(
           self,
           file_path: str,
           known_studios: List[str]
       ) -> Optional[Tuple[str, float]]:
           """Detect studio from file path"""
           
       async def detect_with_ai(
           self,
           scene_data: Dict,
           openai_client: OpenAI
       ) -> Optional[Tuple[str, float]]:
           """Use AI to detect studio"""
           
       def _load_patterns(self) -> Dict[str, re.Pattern]:
           """Load regex patterns for studios"""
   ```

4. **app/services/analysis/performer_detector.py** - Performer detection:
   ```python
   class PerformerDetector:
       async def detect_from_path(
           self,
           file_path: str,
           known_performers: List[str]
       ) -> List[Tuple[str, float]]:
           """Extract performer names from path"""
           
       async def detect_with_ai(
           self,
           scene_data: Dict,
           openai_client: OpenAI
       ) -> List[Tuple[str, float]]:
           """Use AI to detect performers"""
           
       def normalize_name(
           self,
           name: str,
           split_names: bool = False
       ) -> str:
           """Normalize performer name"""
           
       def find_full_name(
           self,
           partial: str,
           known_performers: List[str]
       ) -> Optional[str]:
           """Match partial to full name"""
   ```

5. **app/services/analysis/tag_detector.py** - Tag detection:
   ```python
   class TagDetector:
       async def detect_with_ai(
           self,
           scene_data: Dict,
           openai_client: OpenAI,
           existing_tags: List[str]
       ) -> List[Tuple[str, float]]:
           """Use AI to suggest tags"""
           
       def filter_redundant_tags(
           self,
           tags: List[str],
           existing: List[str]
       ) -> List[str]:
           """Remove redundant/duplicate tags"""
   ```

6. **app/services/analysis/details_generator.py** - Details generation:
   ```python
   class DetailsGenerator:
       async def generate_description(
           self,
           scene_data: Dict,
           openai_client: OpenAI
       ) -> Tuple[str, float]:
           """Generate scene description"""
           
       def clean_html(self, text: str) -> str:
           """Remove HTML from existing details"""
           
       async def enhance_description(
           self,
           current: str,
           scene_data: Dict,
           openai_client: OpenAI
       ) -> Tuple[str, float]:
           """Enhance existing description"""
   ```

### AI Integration

7. **app/services/analysis/ai_client.py** - OpenAI wrapper:
   ```python
   class AIClient:
       def __init__(self, openai_client: OpenAI, model: str):
           self.client = openai_client
           self.model = model
           
       async def analyze_scene(
           self,
           prompt: str,
           scene_data: Dict,
           response_format: Type[BaseModel]
       ) -> BaseModel:
           """Call OpenAI with structured output"""
           
       def estimate_cost(
           self,
           prompt_tokens: int,
           completion_tokens: int
       ) -> float:
           """Estimate API cost"""
           
       def build_prompt(
           self,
           template: str,
           scene_data: Dict
       ) -> str:
           """Build prompt from template"""
   ```

### Prompt Templates

8. **app/services/analysis/prompts.py** - AI prompts:
   ```python
   # Prompt templates for different detection tasks
   
   STUDIO_DETECTION_PROMPT = """
   Analyze the following scene information and identify the studio...
   """
   
   PERFORMER_DETECTION_PROMPT = """
   Extract performer names from the following information...
   """
   
   TAG_SUGGESTION_PROMPT = """
   Suggest relevant tags for this scene...
   """
   
   DESCRIPTION_GENERATION_PROMPT = """
   Generate a concise description for this scene...
   """
   ```

### Plan Management

9. **app/services/analysis/plan_manager.py** - Plan operations:
   ```python
   class PlanManager:
       async def create_plan(
           self,
           name: str,
           changes: List[SceneChanges],
           metadata: Dict,
           db: Session
       ) -> AnalysisPlan:
           """Create and save analysis plan"""
           
       async def get_plan(
           self,
           plan_id: int,
           db: Session
       ) -> Optional[AnalysisPlan]:
           """Retrieve plan with changes"""
           
       async def apply_plan(
           self,
           plan_id: int,
           db: Session,
           stash_service: StashService
       ) -> ApplyResult:
           """Apply plan changes to Stash"""
           
       async def apply_single_change(
           self,
           change: PlanChange,
           db: Session,
           stash_service: StashService
       ) -> bool:
           """Apply individual change"""
   ```

### Batch Processing

10. **app/services/analysis/batch_processor.py** - Batch operations:
    ```python
    class BatchProcessor:
        def __init__(self, batch_size: int = 10):
            self.batch_size = batch_size
            
        async def process_scenes(
            self,
            scenes: List[Scene],
            analyzer: Callable,
            progress_callback: Callable
        ) -> List[SceneChanges]:
            """Process scenes in batches"""
            
        async def process_batch(
            self,
            batch: List[Scene],
            analyzer: Callable
        ) -> List[SceneChanges]:
            """Process single batch concurrently"""
    ```

### Integration with Legacy Logic

11. **app/services/analysis/legacy_adapter.py** - Legacy code adapter:
    ```python
    class LegacyAnalyzer:
        """Adapter for legacy analyze_scenes.py logic"""
        
        def extract_studio_patterns(self) -> Dict:
            """Extract patterns from legacy script"""
            
        def port_detection_logic(self) -> Dict:
            """Port detection algorithms"""
    ```

## Expected Outcome

After completing this task:
- Complete analysis engine is implemented
- AI integration works for all detection types
- Plans can be generated and saved
- Changes can be applied to Stash
- Batch processing is efficient
- Progress is tracked

## Integration Points
- Uses OpenAI for AI detection
- Integrates with StashService
- Saves plans to database
- Reports progress via jobs
- Called by API routes

## Success Criteria
1. Can analyze scenes and detect metadata
2. AI prompts return useful results
3. Confidence scores are meaningful
4. Plans are saved correctly
5. Changes can be applied
6. Batch processing handles large sets
7. Errors are handled gracefully
8. Cost estimation is accurate
9. Legacy logic is preserved