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
        scene_count
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
        scene_count
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