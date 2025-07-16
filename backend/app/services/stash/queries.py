"""GraphQL query definitions for Stash API."""

# Scene fragment with all fields
SCENE_FRAGMENT = """
fragment SceneData on Scene {
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
        duration
        video_codec
        audio_codec
        width
        height
        frame_rate
        bit_rate
    }
    o_counter
}
"""

# Get scenes with pagination
GET_SCENES = (
    """
query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType, $scene_ids: [Int!]) {
    findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids) {
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
        created_at
        updated_at
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
        created_at
        updated_at
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
        created_at
        updated_at
    }
}
"""

# Find scenes with complex filters
FIND_SCENES = (
    """
query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType, $scene_ids: [Int!]) {
    findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids) {
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

# Find performers with updated_at filter
FIND_PERFORMERS_BY_UPDATED = """
query FindPerformers($filter: PerformerFilterType!) {
    findPerformers(performer_filter: $filter) {
        count
        performers {
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
            created_at
            updated_at
        }
    }
}
"""

# Find tags with updated_at filter
FIND_TAGS_BY_UPDATED = """
query FindTags($filter: TagFilterType!) {
    findTags(tag_filter: $filter) {
        count
        tags {
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
            created_at
            updated_at
        }
    }
}
"""

# Find studios with updated_at filter
FIND_STUDIOS_BY_UPDATED = """
query FindStudios($filter: StudioFilterType!) {
    findStudios(studio_filter: $filter) {
        count
        studios {
            id
            name
            url
            details
            rating100
            scene_count
            ignore_auto_tag
            aliases
            created_at
            updated_at
        }
    }
}
"""
