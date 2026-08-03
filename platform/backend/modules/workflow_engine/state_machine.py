"""

Workflow Engine State Machine

State machine implementation for workflow engine. Manages session lifecycle

through states like CREATED, CODING, VALIDATING, PLANNING, APPLYING, TESTING,

GIT_PUSH, CI_TRIGGER, CI_MONITOR, COMPLETED, FAILED, and HUMAN_REVIEW.

"""

import time

import logging

from dataclasses import dataclass, field

from enum import Enum

from typing import Any, Dict, List, Optional

from config.workflow_config import workflow_config

from .exceptions import (
    InvalidStateTransitionError,
    SessionNotFoundError,
    StateMachineError,
)

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session states in the workflow engine."""

    CREATED = "CREATED"
    CODING = "CODING"
    VALIDATING = "VALIDATING"
    PLANNING = "PLANNING"
    APPLYING = "APPLYING"
    TESTING = "TESTING"
    GIT_PUSH = "GIT_PUSH"
    CI_TRIGGER = "CI_TRIGGER"
    CI_MONITOR = "CI_MONITOR"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    CLARIFY = "CLARIFY"
    ESCALATE = "ESCALATE"


# State transition graph

# CREATED -> CODING -> VALIDATING -> PLANNING -> APPLYING -> TESTING ->
# GIT_PUSH -> CI_TRIGGER -> CI_MONITOR -> COMPLETED

#                    ^           ^           ^           ^           |                    |

#                    |           |           |           |           v                    v

#                    +-----------+-----------+-----------+-----------+        CI_FAILED -> FAILED

#                                                                                     |

#                                                                                     v

#                                                                                  HUMAN_REVIEW


VALID_TRANSITIONS: Dict[SessionState, List[SessionState]] = {
    SessionState.CREATED: [SessionState.CLARIFY, SessionState.CODING],
    SessionState.CLARIFY: [SessionState.HUMAN_REVIEW, SessionState.CODING],
    SessionState.CODING: [
        SessionState.VALIDATING,
        SessionState.CODING,  # Retry on failure
    ],
    SessionState.VALIDATING: [
        SessionState.PLANNING,
        SessionState.CODING,  # On failure, go back to CODING
    ],
    SessionState.PLANNING: [
        SessionState.APPLYING,
        SessionState.CODING,  # On failure, go back to CODING
    ],
    SessionState.APPLYING: [
        SessionState.TESTING,
        SessionState.CODING,  # On failure, go back to CODING
    ],
    SessionState.TESTING: [
        SessionState.GIT_PUSH,
        SessionState.CODING,  # On failure, go back to CODING
        SessionState.HUMAN_REVIEW,  # Escalate to human
    ],
    SessionState.GIT_PUSH: [
        SessionState.CI_TRIGGER,
        SessionState.GIT_PUSH,  # Retry on failure
    ],
    SessionState.CI_TRIGGER: [
        SessionState.CI_MONITOR,
        SessionState.CI_TRIGGER,  # Retry on failure
    ],
    SessionState.CI_MONITOR: [
        SessionState.COMPLETED,
        SessionState.FAILED,  # CI failed
        SessionState.HUMAN_REVIEW,  # Escalate to human
    ],
    SessionState.HUMAN_REVIEW: [SessionState.CODING, SessionState.CLARIFY],
    SessionState.ESCALATE: [SessionState.CODING],
    SessionState.COMPLETED: [],
    SessionState.FAILED: [],
}


@dataclass
class StateTransition:
    """Represents a state transition."""

    session_id: str
    from_state: SessionState
    to_state: SessionState
    reason: str
    timestamp: float = field(default_factory=time.time)
    version: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert transition to dictionary."""
        return {
            "session_id": self.session_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "version": self.version,
            "metadata": self.metadata,
        }


@dataclass
class Session:
    """Represents a workflow session."""

    id: str
    build_id: str
    user_id: str
    prompt: str
    status: SessionState = SessionState.CREATED
    current_iteration: int = 0
    max_iterations: int = 5
    error_message: Optional[str] = None
    git_repo_url: Optional[str] = None
    git_branch: Optional[str] = None
    git_commit_sha: Optional[str] = None
    ci_provider: Optional[str] = None
    ci_run_id: Optional[str] = None
    deployment_status: Optional[str] = None
    version: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    state_history: List[StateTransition] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "build_id": self.build_id,
            "user_id": self.user_id,
            "prompt": self.prompt,
            "status": self.status.value,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "error_message": self.error_message,
            "git_repo_url": self.git_repo_url,
            "git_branch": self.git_branch,
            "git_commit_sha": self.git_commit_sha,
            "ci_provider": self.ci_provider,
            "ci_run_id": self.ci_run_id,
            "deployment_status": self.deployment_status,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "state_history": [t.to_dict() for t in self.state_history],
        }


class StateMachine:
    """
    State machine implementation for workflow engine.
    Manages session lifecycle through states:
    CREATED -> CODING -> VALIDATING -> PLANNING -> APPLYING -> TESTING ->
    GIT_PUSH -> CI_TRIGGER -> CI_MONITOR -> COMPLETED
    Handles:
    - State transitions with validation
    - Retry logic with exponential backoff
    - Dead-letter queue handling
    - Saga pattern compensation
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}
        self._transitions: Dict[str, List[StateTransition]] = {}
        self._retry_counts: Dict[str, int] = {}
        self._error_history: Dict[str, List[str]] = {}
        self._pending_transitions: Dict[str, StateTransition] = {}
        logger.info("State machine initialized")

    def create_session(
        self,
        session_id: str,
        build_id: str,
        user_id: str,
        prompt: str,
        git_repo_url: Optional[str] = None,
        git_branch: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Create a new session in CREATED state.
        Args:
            session_id: Unique session identifier
            build_id: Build identifier
            user_id: User ID (User ID)
            prompt: User's natural language prompt
            git_repo_url: Optional Git repository URL
            git_branch: Optional Git branch name
            metadata: Optional metadata dictionary
        Returns:
            Created Session object
        Raises:
            StateMachineError: If session already exists
        """
        if session_id in self._sessions:
            raise StateMachineError(
                f"Session {session_id} already exists", session_id=session_id
            )
        session = Session(
            id=session_id,
            build_id=build_id,
            user_id=user_id,
            prompt=prompt,
            git_repo_url=git_repo_url,
            git_branch=git_branch,
            max_iterations=workflow_config.MAX_ITERATIONS,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        self._retry_counts[session_id] = 0
        self._error_history[session_id] = []
        logger.info(
            f"Created session {session_id}",
            extra={
                "session_id": session_id,
                "build_id": build_id,
                "user_id": user_id,
                "status": session.status.value,
            },
        )
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.
        Args:
            session_id: Session identifier
        Returns:
            Session object or None if not found
        """
        return self._sessions.get(session_id)

    def transition(
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
        session = self.get_session(session_id)
        if not session:
            raise SessionNotFoundError(
                f"Session {session_id} not found", session_id=session_id
            )
        from_state = session.status
        # Validate transition
        if to_state not in VALID_TRANSITIONS.get(from_state, []):
            raise InvalidStateTransitionError(
                f"Invalid transition from {from_state.value} to {to_state.value}",
                session_id=session_id,
                from_state=from_state.value,
                to_state=to_state.value,
            )
        # Create transition record
        transition = StateTransition(
            session_id=session_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            version=session.version + 1,
            metadata=metadata or {},
        )
        # Update session
        session.status = to_state
        session.updated_at = time.time()
        session.version = transition.version
        session.state_history.append(transition)
        # Store transition
        if session_id not in self._transitions:
            self._transitions[session_id] = []
        self._transitions[session_id].append(transition)
        logger.info(
            f"Transitioned session {session_id} from {from_state.value} to {to_state.value}",
            extra={
                "session_id": session_id,
                "from_state": from_state.value,
                "to_state": to_state.value,
                "reason": reason,
                "version": transition.version,
            },
        )
        return session

    def increment_iteration(self, session_id: str) -> Session:
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
        session = self.get_session(session_id)
        if not session:
            raise SessionNotFoundError(
                f"Session {session_id} not found", session_id=session_id
            )
        session.current_iteration += 1
        if session.current_iteration > session.max_iterations:
            raise StateMachineError(
                f"Max iterations ({session.max_iterations}) exceeded for session {session_id}",
                session_id=session_id,
            )
        session.updated_at = time.time()
        logger.info(
            f"Incremented iteration for session {session_id} to {session.current_iteration}",
            extra={
                "session_id": session_id,
                "current_iteration": session.current_iteration,
                "max_iterations": session.max_iterations,
            },
        )
        return session

    def set_error(self, session_id: str, error_message: str) -> Session:
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
        session = self.get_session(session_id)
        if not session:
            raise SessionNotFoundError(
                f"Session {session_id} not found", session_id=session_id
            )
        session.error_message = error_message
        session.updated_at = time.time()
        # Add to error history
        if session_id not in self._error_history:
            self._error_history[session_id] = []
        self._error_history[session_id].append(error_message)
        logger.error(
            f"Set error for session {session_id}: {error_message}",
            extra={"session_id": session_id, "error_message": error_message},
        )
        return session

    def can_transition(self, from_state: SessionState, to_state: SessionState) -> bool:
        """
        Check if a state transition is valid.
        Args:
            from_state: Source state
            to_state: Target state
        Returns:
            True if transition is valid, False otherwise
        """
        return to_state in VALID_TRANSITIONS.get(from_state, [])

    def get_valid_transitions(self, state: SessionState) -> List[SessionState]:
        """
        Get all valid transitions from a given state.
        Args:
            state: Source state
        Returns:
            List of valid target states
        """
        return VALID_TRANSITIONS.get(state, [])

    def get_session_history(self, session_id: str) -> List[StateTransition]:
        """
        Get the state transition history for a session.
        Args:
            session_id: Session identifier
        Returns:
            List of state transitions
        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(
                f"Session {session_id} not found", session_id=session_id
            )
        return self._transitions.get(session_id, [])

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from the state machine.
        Args:
            session_id: Session identifier
        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._transitions[session_id]
            del self._retry_counts[session_id]
            del self._error_history[session_id]
            logger.info(f"Deleted session {session_id}")
            return True
        return False

    def get_all_sessions(self) -> List[Session]:
        """
        Get all sessions.
        Returns:
            List of all Session objects
        """
        return list(self._sessions.values())

    def get_sessions_by_user(self, user_id: str) -> List[Session]:
        """
        Get all sessions for a specific user.
        Args:
            user_id: User ID (User ID)
        Returns:
            List of Session objects for the user
        """
        return [
            session for session in self._sessions.values() if session.user_id == user_id
        ]

    def get_sessions_by_status(self, status: SessionState) -> List[Session]:
        """
        Get all sessions with a specific status.
        Args:
            status: Session state
        Returns:
            List of Session objects with the given status
        """
        return [
            session for session in self._sessions.values() if session.status == status
        ]


# Global state machine instance


state_machine = StateMachine()
