"""

Session Manager

Manages workflow session lifecycle, persistence, and integration

with the database adapter.

"""

import logging

import uuid

from typing import Optional, Dict, Any, List

from .state_machine import StateMachine, Session, SessionState

from .exceptions import SessionNotFoundError

from db.adapters.persistence_adapter import persistence_adapter

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages workflow sessions with persistence.
    This class provides:
    - Session CRUD operations
    - State transition management
    - Iteration tracking
    - Error handling
    - Database persistence
    """

    def __init__(self) -> None:
        self.state_machine = StateMachine()
        logger.info("Session manager initialized")

    async def create_session(
        self,
        build_id: str,
        user_id: str,
        prompt: str,
        session_id: Optional[str] = None,
        git_repo_url: Optional[str] = None,
        git_branch: Optional[str] = None,
        ci_provider: Optional[str] = None,
        ci_inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Create a new workflow session.
        Args:
            build_id: Unique build identifier
            user_id: User ID (User ID)
            prompt: User's natural language prompt
            session_id: Optional explicit session identifier (defaults to random UUID)
            git_repo_url: Optional Git repository URL
            git_branch: Optional Git branch name
            ci_provider: Optional CI provider
            ci_inputs: Optional CI workflow inputs
            metadata: Optional metadata dictionary
        Returns:
            Created Session object
        """
        session_id = session_id if session_id else str(uuid.uuid4())
        # Create session in state machine
        session = self.state_machine.create_session(
            session_id=session_id,
            build_id=build_id,
            user_id=user_id,
            prompt=prompt,
            git_repo_url=git_repo_url,
            git_branch=git_branch,
            metadata=metadata,
        )
        # Persist to database
        try:
            persistence_adapter.create_session(
                session_id=session_id,
                build_id=build_id,
                user_id=user_id,
                prompt=prompt,
                git_repo_url=git_repo_url,
                git_branch=git_branch,
                ci_provider=ci_provider,
                ci_inputs=ci_inputs or {},
            )
            logger.info(f"Session {session_id} persisted to database")
        except Exception as e:
            logger.error(f"Failed to persist session {session_id}: {str(e)}")
            # Continue anyway - session is in memory
        return session

    async def get_session(self, session_id: str) -> Session:
        """
        Get a session by ID.
        Args:
            session_id: Session identifier
        Returns:
            Session object
        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        # Try to get from state machine first
        session = self.state_machine.get_session(session_id)
        if session:
            return session
        # If not in memory, try to load from database
        try:
            db_session = persistence_adapter.get_session(session_id)
            if db_session:
                # Recreate session in state machine
                session = Session(
                    id=db_session.get("id"),  # type: ignore[arg-type]
                    build_id=db_session.get("build_id"),  # type: ignore[arg-type]
                    user_id=db_session.get("user_id"),  # type: ignore[arg-type]
                    prompt=db_session.get("prompt"),  # type: ignore[arg-type]
                    status=SessionState(db_session.get("status", "CREATED")),
                    current_iteration=db_session.get("current_iteration", 0),
                    error_message=db_session.get("error_message"),
                    git_repo_url=db_session.get("git_repo_url"),
                    git_branch=db_session.get("git_branch"),
                    git_commit_sha=db_session.get("git_commit_sha"),
                    ci_provider=db_session.get("ci_provider"),
                    ci_run_id=db_session.get("ci_run_id"),
                    deployment_status=db_session.get("deployment_status"),
                    version=db_session.get("version", 0),
                    created_at=db_session.get("created_at", 0),
                    updated_at=db_session.get("updated_at", 0),
                    metadata=db_session.get("metadata", {}),
                )
                # Add to state machine
                self.state_machine._sessions[session_id] = session
                return session
        except Exception as e:
            logger.error(f"Failed to load session {session_id} from database: {str(e)}")
        raise SessionNotFoundError(
            f"Session {session_id} not found", session_id=session_id
        )

    async def transition_session(
        self,
        session_id: str,
        to_state: SessionState,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Transition a session to a new state.
        Args:
            session_id: Session identifier
            to_state: Target state
            reason: Reason for transition
            metadata: Optional metadata for transition
        Returns:
            Updated Session object
        Raises:
            SessionNotFoundError: If session doesn't exist
            InvalidStateTransitionError: If transition is invalid
        """
        # Transition in state machine
        session = self.state_machine.transition(
            session_id=session_id, to_state=to_state, reason=reason, metadata=metadata
        )
        # Persist to database
        try:
            persistence_adapter.update_session_status(
                session_id=session_id,
                status=to_state.value,
                current_iteration=session.current_iteration,
                git_repo_url=session.git_repo_url,
                git_branch=session.git_branch,
                git_commit_sha=session.git_commit_sha,
                ci_provider=session.ci_provider,
                ci_run_id=session.ci_run_id,
                deployment_status=session.deployment_status,
            )
        except Exception as e:
            logger.error(
                f"Failed to persist transition for session {session_id}: {str(e)}"
            )
        return session

    async def increment_iteration(self, session_id: str) -> Session:
        """
        Increment the iteration counter for a session.
        Args:
            session_id: Session identifier
        Returns:
            Updated Session object
        Raises:
            SessionNotFoundError: If session doesn't exist
            StateMachineError: If max iterations exceeded
        """
        session = self.state_machine.increment_iteration(session_id)
        # Persist to database
        try:
            persistence_adapter.update_session_status(
                session_id=session_id, current_iteration=session.current_iteration
            )
        except Exception as e:
            logger.error(
                f"Failed to persist iteration for session {session_id}: {str(e)}"
            )
        return session

    async def set_error(self, session_id: str, error_message: str) -> Session:
        """
        Set an error message for a session.
        Args:
            session_id: Session identifier
            error_message: Error message
        Returns:
            Updated Session object
        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        session = self.state_machine.set_error(session_id, error_message)
        # Persist to database
        try:
            persistence_adapter.update_session_status(
                session_id=session_id, error_message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to persist error for session {session_id}: {str(e)}")
        return session

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionState] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Session]:
        """
        List sessions with optional filters.
        Args:
            user_id: Optional user ID filter
            status: Optional status filter
            limit: Maximum number of sessions to return
            offset: Offset for pagination
        Returns:
            List of Session objects
        """
        sessions = self.state_machine.get_all_sessions()
        # Apply filters
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        if status:
            sessions = [s for s in sessions if s.status == status]
        # Apply pagination
        return sessions[offset : offset + limit]

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        Args:
            session_id: Session identifier
        Returns:
            True if session was deleted, False if not found
        """
        # Delete from state machine
        result = self.state_machine.delete_session(session_id)
        if result:
            # Delete from database
            try:
                # Note: persistence_adapter would need a delete method
                logger.info(f"Session {session_id} deleted")
            except Exception as e:
                logger.error(
                    f"Failed to delete session {session_id} from database: {str(e)}"
                )
        return bool(result)


# Global session manager instance


session_manager = SessionManager()
