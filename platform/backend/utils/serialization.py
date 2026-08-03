"""

Serialization utilities for handling datetime objects and other non-JSON-serializable types

"""

from datetime import datetime

from typing import Any, Dict, List, Union

import json


def serialize_datetime(obj: Any) -> Union[str, Any]:
    """
    Convert datetime objects to ISO 8601 strings for JSON serialization
    Args:
        obj: Object to serialize
    Returns:
        ISO 8601 string if datetime, otherwise original object
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def serialize_model_config(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Recursively serialize model configuration data, converting datetime objects
    Args:
        data: Data to serialize (dict, list, or primitive type)
    Returns:
        Serialized data with datetime objects converted to ISO strings
    """
    if isinstance(data, dict):
        return {key: serialize_model_config(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_model_config(item) for item in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data


def prepare_db_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare data for DB storage by converting datetime objects
    Args:
        data: Dictionary to prepare for DB storage
    Returns:
        Dictionary with datetime objects converted to ISO strings
    """
    result = serialize_model_config(data)
    if isinstance(result, dict):
        return result
    else:
        raise ValueError("Expected dictionary for DB data")


# Deprecated alias for backwards compatibility
prepare_firestore_data = prepare_db_data


def prepare_api_response(data: Any) -> Dict[str, Any]:
    """
    Prepare data for API response by converting datetime objects
    Args:
        data: Data to prepare for API response
    Returns:
        Data with datetime objects converted to ISO strings
    """
    result = serialize_model_config(data)
    if isinstance(result, dict):
        return result
    raise ValueError("Expected dictionary for API response")


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
