"""

Metadata Manager

Manages artifact metadata with validation and enrichment.

"""

import logging

from typing import Dict, Any, List, Optional

from datetime import datetime

logger = logging.getLogger(__name__)


class MetadataManager:
    """
    Manager for artifact metadata operations.
    Features:
    - Metadata validation
    - Enrichment with system data
    - Schema validation
    - Version tracking
    """

    def __init__(self) -> None:
        logger.info("Metadata manager initialized")

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and enrich artifact metadata.
        Args:
            metadata: Raw metadata dictionary
        Returns:
            Validated and enriched metadata
        """
        validated: Dict[str, Any] = {}
        # Validate description
        if "description" in metadata:
            description = metadata["description"]
            if not isinstance(description, str) or len(description) > 1000:
                logger.warning(f"Invalid description: {description}")
            else:
                validated["description"] = description
        # Validate format
        if "format" in metadata:
            format = metadata["format"]
            valid_formats = [
                "json",
                "yaml",
                "hcl",
                "tf",
                "dockerfile",
                "shell",
                "markdown",
            ]
            if format not in valid_formats:
                logger.warning(f"Invalid format: {format}")
            else:
                validated["format"] = format
        # Validate tags
        if "tags" in metadata:
            tags = metadata["tags"]
            if isinstance(tags, list):
                if not all(isinstance(t, str) for t in tags):
                    logger.warning(f"Invalid tags: {tags}")
                else:
                    validated["tags"] = list(tags)
            else:
                validated["tags"] = []
        # Validate version
        if "version" in metadata:
            version = metadata["version"]
            if not isinstance(version, str):
                logger.warning(f"Invalid version: {version}")
            else:
                validated["version"] = version
        # Add system metadata
        validated["validated_at"] = datetime.now().isoformat()
        validated["enriched"] = True
        logger.debug(f"Validated metadata: {validated}")
        return validated

    def create_artifact_metadata(
        self,
        session_id: str,
        iteration_num: int,
        artifact_type: str,
        filename: str,
        user_id: str,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create metadata for a new artifact.
        Args:
            session_id: Session identifier
            iteration_num: Iteration number
            artifact_type: Type of artifact
            filename: Original filename
            user_id: User ID for ownership
            additional_metadata: Optional additional metadata
        Returns:
            Complete metadata dictionary
        """
        metadata = {
            "session_id": session_id,
            "iteration_num": iteration_num,
            "type": artifact_type,
            "filename": filename,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
        }
        # Add additional metadata
        if additional_metadata:
            metadata.update(additional_metadata)
        # Validate and enrich
        return self.validate_metadata(metadata)

    def update_artifact_metadata(
        self, artifact_id: str, metadata_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update metadata for an existing artifact.
        Args:
            artifact_id: Artifact identifier
            metadata_updates: Dictionary of fields to update
        Returns:
            Updated metadata dictionary
        """
        # Add updated_at timestamp
        metadata_updates["updated_at"] = datetime.now().isoformat()
        logger.info(f"Updated metadata for artifact {artifact_id}")
        return metadata_updates

    def get_artifact_history(
        self, session_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get history of metadata changes for an artifact.
        Args:
            session_id: Session identifier
            limit: Maximum number of history entries
        Returns:
            List of metadata change records
        """
        # This would require a separate metadata_history table
        # For now, return empty list
        logger.info(f"Retrieved artifact history for session {session_id}")
        return []


# Global metadata manager instance


metadata_manager = MetadataManager()
