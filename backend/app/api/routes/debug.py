"""
Debug endpoints for development and troubleshooting.
"""

from typing import Any, Dict, List, Union, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession

from app.core.dependencies import get_db, get_stash_service
from app.services.stash_service import StashService

router = APIRouter()


@router.get("/pending-scenes-debug")
async def debug_pending_scenes(
    stash_service: StashService = Depends(get_stash_service),
    db: AsyncDBSession = Depends(get_db),
) -> Dict[str, Any]:
    """Debug endpoint to troubleshoot pending scenes detection."""
    from sqlalchemy import select

    from app.models import SyncHistory

    # Get last scene sync
    query = (
        select(SyncHistory)
        .where(
            SyncHistory.entity_type == "scene",
            SyncHistory.status == "completed",
        )
        .order_by(SyncHistory.completed_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    last_sync = result.scalar_one_or_none()

    debug_info: Dict[str, Union[None, int, List[Any], Dict[str, Any]]] = {
        "last_sync": None,
        "test_queries": [],
        "all_scenes_count": 0,
        "recent_scenes": [],
    }

    if last_sync:
        debug_info["last_sync"] = {
            "completed_at": (
                last_sync.completed_at.isoformat() if last_sync.completed_at else None
            ),
            "completed_at_raw": str(last_sync.completed_at),
            "timezone_info": (
                str(last_sync.completed_at.tzinfo) if last_sync.completed_at else None
            ),
        }

        # Test different timestamp formats
        if last_sync.completed_at:
            timestamp_variations = [
                last_sync.completed_at.isoformat(),
                last_sync.completed_at.strftime("%Y-%m-%dT%H:%M:%S%z"),
                last_sync.completed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                last_sync.completed_at.isoformat().replace("+00:00", "Z"),
            ]

            for idx, ts_format in enumerate(timestamp_variations):
                filter_dict = {
                    "updated_at": {
                        "value": ts_format,
                        "modifier": "GREATER_THAN",
                    }
                }

                try:
                    _, count = await stash_service.get_scenes(
                        page=1, per_page=1, filter=filter_dict
                    )
                    cast(List[Any], debug_info["test_queries"]).append(
                        {
                            "format_index": idx,
                            "timestamp_format": ts_format,
                            "filter": filter_dict,
                            "count": count,
                            "success": True,
                        }
                    )
                except Exception as e:
                    cast(List[Any], debug_info["test_queries"]).append(
                        {
                            "format_index": idx,
                            "timestamp_format": ts_format,
                            "filter": filter_dict,
                            "error": str(e),
                            "success": False,
                        }
                    )

    # Get total scene count
    _, total = await stash_service.get_scenes(page=1, per_page=1)
    debug_info["all_scenes_count"] = total

    # Get 5 most recent scenes
    recent_scenes, _ = await stash_service.get_scenes(
        page=1, per_page=5, sort="updated_at"
    )
    debug_info["recent_scenes"] = [
        {
            "id": s.get("id"),
            "title": s.get("title", ""),
            "updated_at": s.get("updated_at"),
            "created_at": s.get("created_at"),
        }
        for s in recent_scenes
    ]

    return debug_info


# Custom debug query for scenes
DEBUG_SCENE_QUERY = """
query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType, $scene_ids: [Int!]) {
  findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids) {
    count
    scenes {
      id
      title
      urls
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
      scene_markers{
        id
        created_at
        updated_at
        primary_tag{
          id
          name
        }
        seconds
        end_seconds
        tags{
          id
          name
        }
        title
      }
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


# Custom debug query for markers
DEBUG_MARKER_QUERY = """
query FindSceneMarkers($filter: FindFilterType, $scene_marker_filter: SceneMarkerFilterType, $ids: [ID!]) {
  findSceneMarkers(filter: $filter, scene_marker_filter: $scene_marker_filter, ids: $ids) {
    count
    scene_markers {
      id
      title
      seconds
      end_seconds
      created_at
      updated_at
      stream
      preview
      screenshot
      scene {
        id
        title
        date
        rating100
        organized
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
          bit_rate
        }
        studio {
          id
          name
        }
        performers {
          id
          name
          gender
        }
        tags {
          id
          name
        }
      }
      primary_tag {
        id
        name
        aliases
        ignore_auto_tag
        favorite
        description
        parent_count
        child_count
        parents {
          id
          name
        }
        children {
          id
          name
        }
      }
      tags {
        id
        name
        aliases
        ignore_auto_tag
        favorite
        description
        parent_count
        child_count
        parents {
          id
          name
        }
        children {
          id
          name
        }
      }
    }
  }
}
"""


@router.get("/stashmarker/{marker_id}")
async def get_stash_marker_debug(
    marker_id: str,
    stash_service: StashService = Depends(get_stash_service),
) -> Dict[str, Any]:
    """
    Get raw marker data from Stash GraphQL API for debugging purposes.

    Returns both the GraphQL query and the raw result.
    """
    # Format the query for display with variables filled in
    query_for_display = DEBUG_MARKER_QUERY.strip()
    # Replace the variable declarations and usage with actual values
    query_for_display = query_for_display.replace(
        "query FindSceneMarkers($filter: FindFilterType, $scene_marker_filter: SceneMarkerFilterType, $ids: [ID!])",
        "query FindSceneMarkers",
    )
    query_for_display = query_for_display.replace(
        "findSceneMarkers(filter: $filter, scene_marker_filter: $scene_marker_filter, ids: $ids)",
        f'findSceneMarkers(ids: ["{marker_id}"])',
    )
    # Convert to single line by removing newlines and collapsing multiple spaces
    query_for_display = " ".join(query_for_display.split())

    try:
        # Execute the GraphQL query with ids filter
        result = await stash_service.execute_graphql(
            DEBUG_MARKER_QUERY, {"ids": [marker_id]}
        )

        # Check if marker was found
        if not result.get("findSceneMarkers") or not result["findSceneMarkers"].get(
            "scene_markers"
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Marker {marker_id} not found in Stash",
            )

        return {"query": query_for_display, "result": result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch marker from Stash: {str(e)}",
        )
