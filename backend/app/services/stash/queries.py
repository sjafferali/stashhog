"""GraphQL query definitions for Stash API."""

# Scene fragment with all fields
SCENE_FRAGMENT = """
fragment SceneData on Scene {
    id
    title
    paths {
        path
        stream
        caption
        funscript
        interactive
        interactive_speed
    }
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
        path
    }
    file {
        size
        duration
        video_codec
        audio_codec
        width
        height
        framerate
        bitrate
    }
    o_counter
    interactive
    interactive_speed
}
"""

# Get scenes with pagination
GET_SCENES = (
    """
query FindScenes($filter: SceneFilterType, $scene_filter: SceneFilter, $scene_ids: [Int!], $page: Int, $per_page: Int, $sort: String, $direction: SortDirectionEnum) {
    findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids, page: $page, per_page: $per_page, sort: $sort, direction: $direction) {
        count
        scenes {
            ...SceneData
        }
    }
}
"""
    + SCENE_FRAGMENT
)

# Get single scene by ID
GET_SCENE_BY_ID = (
    """
query FindScene($id: ID!) {
    findScene(id: $id) {
        ...SceneData
    }
}
"""
    + SCENE_FRAGMENT
)

# Get all performers
GET_ALL_PERFORMERS = """
query AllPerformers {
    allPerformers {
        id
        name
        gender
        url
        twitter
        instagram
        birthdate
        ethnicity
        country
        eye_color
        height_cm
        measurements
        fake_tits
        career_length
        tattoos
        piercings
        alias_list
        favorite
        rating100
        details
        death_date
        hair_color
        weight
        ignore_auto_tag
    }
}
"""

# Get all tags
GET_ALL_TAGS = """
query AllTags {
    allTags {
        id
        name
        description
        aliases
        ignore_auto_tag
        scene_count
        performer_count
        studio_count
        movie_count
        gallery_count
        image_count
    }
}
"""

# Get all studios
GET_ALL_STUDIOS = """
query AllStudios {
    allStudios {
        id
        name
        url
        details
        rating100
        scene_count
        ignore_auto_tag
        aliases
    }
}
"""

# Find scenes with complex filters
FIND_SCENES = (
    """
query FindScenes($filter: SceneFilterType, $scene_filter: SceneFilter, $scene_ids: [Int!], $page: Int, $per_page: Int, $sort: String, $direction: SortDirectionEnum) {
    findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids, page: $page, per_page: $per_page, sort: $sort, direction: $direction) {
        count
        scenes {
            ...SceneData
        }
    }
}
"""
    + SCENE_FRAGMENT
)

# Get stats
GET_STATS = """
query Stats {
    stats {
        scene_count
        performer_count
        studio_count
        movie_count
        tag_count
        total_o_count
        total_play_duration
        total_play_count
        scenes_size
        scenes_duration
        image_count
        images_size
        gallery_count
        galleries_size
        performer_count
        unique_performer_count
        movie_count
        total_size
        total_duration
    }
}
"""

# Test connection
TEST_CONNECTION = """
query Version {
    version {
        version
        hash
        build_time
    }
}
"""

# Find performer by name
FIND_PERFORMER = """
query FindPerformers($filter: PerformerFilterType!) {
    findPerformers(filter: $filter, limit: 10) {
        performers {
            id
            name
            gender
            url
            birthdate
            favorite
            rating100
        }
    }
}
"""

# Find tag by name
FIND_TAG = """
query FindTags($filter: TagFilterType!) {
    findTags(filter: $filter, limit: 10) {
        tags {
            id
            name
            description
            aliases
            scene_count
        }
    }
}
"""

# Find studio by name
FIND_STUDIO = """
query FindStudios($filter: StudioFilterType!) {
    findStudios(filter: $filter, limit: 10) {
        studios {
            id
            name
            url
            details
            rating100
            scene_count
        }
    }
}
"""
