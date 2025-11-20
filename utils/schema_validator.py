"""
Schema validation utilities
"""

import jsonschema
from typing import Dict, List, Tuple

# Reddit post schema
REDDIT_POST_SCHEMA = {
    "type": "object",
    "required": ["id", "title", "author", "created_utc", "subreddit"],
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "selftext": {"type": ["string", "null"]},
        "author": {"type": "string"},
        "subreddit": {"type": "string"},
        "created_utc": {"type": "string"},
        "score": {"type": ["integer", "null"]},
        "num_comments": {"type": ["integer", "null"]},
        "url": {"type": ["string", "null"]},
        "permalink": {"type": ["string", "null"]},
        "upvote_ratio": {"type": ["number", "null"]},
        "is_self": {"type": ["boolean", "null"]},
        "link_flair_text": {"type": ["string", "null"]}
    }
}


def validate_reddit_post(post: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a Reddit post against schema
    
    Args:
        post: Post dictionary to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        jsonschema.validate(instance=post, schema=REDDIT_POST_SCHEMA)
        return True, []
    except jsonschema.exceptions.ValidationError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]


def check_data_completeness(post: Dict, required_fields: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if required fields are present and non-null
    
    Args:
        post: Post dictionary
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_complete, list_of_missing_fields)
    """
    missing = []
    for field in required_fields:
        if field not in post or post[field] is None or post[field] == "":
            missing.append(field)
    
    return len(missing) == 0, missing