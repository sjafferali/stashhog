"""GraphQL mutation definitions for Stash API."""

# Update scene
UPDATE_SCENE = """
mutation SceneUpdate($input: SceneUpdateInput!) {
    sceneUpdate(input: $input) {
        id
        title
        details
        date
        rating100
        organized
        studio {
            id
            name
        }
        performers {
            id
            name
        }
        tags {
            id
            name
        }
    }
}
"""

# Create performer
CREATE_PERFORMER = """
mutation PerformerCreate($input: PerformerCreateInput!) {
    performerCreate(input: $input) {
        id
        name
        gender
        url
        birthdate
        favorite
        rating100
    }
}
"""

# Create tag
CREATE_TAG = """
mutation TagCreate($input: TagCreateInput!) {
    tagCreate(input: $input) {
        id
        name
        description
        aliases
    }
}
"""

# Create studio
CREATE_STUDIO = """
mutation StudioCreate($input: StudioCreateInput!) {
    studioCreate(input: $input) {
        id
        name
        url
        details
        rating100
    }
}
"""

# Bulk update scenes
BULK_UPDATE_SCENES = """
mutation BulkSceneUpdate($input: BulkSceneUpdateInput!) {
    bulkSceneUpdate(input: $input) {
        id
        title
        details
        date
        rating100
        organized
        studio {
            id
            name
        }
        performers {
            id
            name
        }
        tags {
            id
            name
        }
    }
}
"""

# Update performer
UPDATE_PERFORMER = """
mutation PerformerUpdate($input: PerformerUpdateInput!) {
    performerUpdate(input: $input) {
        id
        name
        gender
        url
        birthdate
        favorite
        rating100
    }
}
"""

# Update tag
UPDATE_TAG = """
mutation TagUpdate($input: TagUpdateInput!) {
    tagUpdate(input: $input) {
        id
        name
        description
        aliases
    }
}
"""

# Update studio
UPDATE_STUDIO = """
mutation StudioUpdate($input: StudioUpdateInput!) {
    studioUpdate(input: $input) {
        id
        name
        url
        details
        rating100
    }
}
"""

# Create scene marker
CREATE_SCENE_MARKER = """
mutation SceneMarkerCreate($input: SceneMarkerCreateInput!) {
    sceneMarkerCreate(input: $input) {
        id
        title
        seconds
        end_seconds
        primary_tag {
            id
            name
        }
        tags {
            id
            name
        }
        scene {
            id
        }
    }
}
"""

# Delete scene marker
DELETE_SCENE_MARKER = """
mutation SceneMarkerDestroy($id: ID!) {
    sceneMarkerDestroy(id: $id)
}
"""

# Generate metadata
METADATA_GENERATE = """
mutation GenerateMetadata($input: GenerateMetadataInput!) {
    metadataGenerate(input: $input)
}
"""

# Stop job
STOP_JOB = """
mutation StopJob($job_id: ID!) {
    stopJob(job_id: $job_id)
}
"""

# Delete tag
DELETE_TAG = """
mutation TagDestroy($input: TagDestroyInput!) {
    tagDestroy(input: $input)
}
"""
