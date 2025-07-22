"""
Debug endpoints for development and troubleshooting.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_stash_service
from app.services.stash_service import StashService

router = APIRouter()

# Custom debug query for scenes
DEBUG_SCENE_QUERY = """
query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType, $scene_ids: [Int!]) {
  findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids) {
    count
    scenes {
      id
      title
      paths {
        screenshot
        preview
        stream
        webp
        vtt
        sprite
        funscript
        interactive_heatmap
        caption
      }
      interactive
      interactive_speed
      organized
      details
      created_at
      updated_at
      date
      rating100
      studio {
        id
        name
      }
      performers {
        id
        name
        gender
        favorite
        rating100
      }
      tags {
        id
        name
      }
      movies {
        movie {
          id
          name
        }
        scene_index
      }
      galleries {
        id
        title
        paths {
          cover
          preview
        }
      }
      files {
        path
        size
        id
        duration
        video_codec
        audio_codec
        width
        height
        frame_rate
        fingerprints{
          value
          type
        }
        bit_rate
      }
      o_counter
    }
  }
}
"""


@router.get("/stashscene/{scene_id}")
async def get_stash_scene_debug(
    scene_id: str,
    stash_service: StashService = Depends(get_stash_service),
) -> Dict[str, Any]:
    """
    Get raw scene data from Stash GraphQL API for debugging purposes.

    Returns both the GraphQL query and the raw result.
    """
    # Convert scene_id to int for the query (Stash uses Int IDs)
    try:
        scene_id_int = int(scene_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scene ID: {scene_id}",
        )

    # Format the query for display with variables filled in
    query_for_display = DEBUG_SCENE_QUERY.strip()
    # Replace the variable declarations and usage with actual values
    query_for_display = query_for_display.replace(
        "query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType, $scene_ids: [Int!])",
        "query FindScenes",
    )
    query_for_display = query_for_display.replace(
        "findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids)",
        f"findScenes(scene_ids: [{scene_id_int}])",
    )
    # Convert to single line by removing newlines and collapsing multiple spaces
    query_for_display = " ".join(query_for_display.split())

    try:
        # Execute the GraphQL query with scene_ids filter
        result = await stash_service.execute_graphql(
            DEBUG_SCENE_QUERY, {"scene_ids": [scene_id_int]}
        )

        # Check if scene was found
        if not result.get("findScenes") or not result["findScenes"].get("scenes"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scene {scene_id} not found in Stash",
            )

        return {"query": query_for_display, "result": result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch scene from Stash: {str(e)}",
        )
