"""

Transition Handler

Handles state transitions with validation, side effects, and

integration with other modules.

"""

import logging

from typing import Dict, Any, Optional, Callable, List

from .state_machine import SessionState, Session, state_machine

from .exceptions import InvalidStateTransitionError

logger = logging.getLogger(__name__)


class TransitionHandler:
    """
    Handles state transitions with side effects.
    Features:
    - Transition validation
    - Side effect execution
    - Transition hooks
    - Error handling
    """

    def __init__(self) -> None:
        self._transition_hooks: Dict[SessionState, List[Callable]] = {}
        self._side_effects: Dict[tuple, Callable] = {}
        logger.info("Transition handler initialized")

    def register_hook(
        self, state: SessionState, hook: Callable[[Session], None]
    ) -> None:
        """
        Register a hook to be called when entering a state.
        Args:
            state: State to hook into
            hook: Function to call when entering state
        """
        if state not in self._transition_hooks:
            self._transition_hooks[state] = []
        self._transition_hooks[state].append(hook)
        logger.debug(
            f"Registered hook for state {state.value}", extra={"state": state.value}
        )

    def register_side_effect(
        self,
        from_state: SessionState,
        to_state: SessionState,
        effect: Callable[[Session], None],
    ) -> None:
        """
        Register a side effect for a specific transition.
        Args:
            from_state: Source state
            to_state: Target state
            effect: Function to call during transition
        """
        key = (from_state, to_state)
        self._side_effects[key] = effect
        logger.debug(
            f"Registered side effect for {from_state.value} -> {to_state.value}",
            extra={"from_state": from_state.value, "to_state": to_state.value},
        )

    async def execute_transition(
        self,
        session: Session,
        to_state: SessionState,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Execute a state transition with hooks and side effects.
        Args:
            session: Session object
            to_state: Target state
            reason: Reason for transition
            metadata: Optional metadata
        Returns:
            Updated Session object
        Raises:
            InvalidStateTransitionError: If transition is invalid
            StateMachineError: If transition execution fails
        """
        from_state = session.status
        logger.info(
            f"Executing transition: {from_state.value} -> {to_state.value}",
            extra={
                "session_id": session.id,
                "from_state": from_state.value,
                "to_state": to_state.value,
                "reason": reason,
            },
        )
        # Validate transition
        if not state_machine.can_transition(from_state, to_state):
            raise InvalidStateTransitionError(
                f"Invalid transition from {from_state.value} to {to_state.value}",
                session_id=session.id,
                from_state=from_state.value,
                to_state=to_state.value,
            )
        # Execute exit hooks for current state
        if from_state in self._transition_hooks:
            for hook in self._transition_hooks[from_state]:
                try:
                    hook(session)
                    logger.debug(
                        f"Executed exit hook for {from_state.value}",
                        extra={"session_id": session.id, "state": from_state.value},
                    )
                except Exception as e:
                    logger.error(
                        f"Exit hook failed for {from_state.value}: {str(e)}",
                        extra={
                            "session_id": session.id,
                            "state": from_state.value,
                            "error": str(e),
                        },
                    )
        # Execute side effects for transition
        transition_key = (from_state, to_state)
        if transition_key in self._side_effects:
            try:
                self._side_effects[transition_key](session)
                logger.debug(
                    f"Executed side effect for {from_state.value} -> {to_state.value}",
                    extra={
                        "session_id": session.id,
                        "from_state": from_state.value,
                        "to_state": to_state.value,
                    },
                )
            except Exception as e:
                logger.error(
                    f"Side effect failed for {from_state.value} -> {to_state.value}: {str(e)}",
                    extra={
                        "session_id": session.id,
                        "from_state": from_state.value,
                        "to_state": to_state.value,
                        "error": str(e),
                    },
                )
        # Perform transition
        session = state_machine.transition(
            session_id=session.id, to_state=to_state, reason=reason, metadata=metadata
        )
        # Execute entry hooks for new state
        if to_state in self._transition_hooks:
            for hook in self._transition_hooks[to_state]:
                try:
                    hook(session)
                    logger.debug(
                        f"Executed entry hook for {to_state.value}",
                        extra={"session_id": session.id, "state": to_state.value},
                    )
                except Exception as e:
                    logger.error(
                        f"Entry hook failed for {to_state.value}: {str(e)}",
                        extra={
                            "session_id": session.id,
                            "state": to_state.value,
                            "error": str(e),
                        },
                    )
        return session

    def get_valid_transitions(
        self, session: Session, state: SessionState
    ) -> List[SessionState]:
        """
        Get all valid transitions from a state.
        Args:
            session: Session object with state machine
            state: Source state
        Returns:
            List of valid target states
        """
        return state_machine.get_valid_transitions(state)

    def get_transition_history(self, session: Session) -> List[Dict[str, Any]]:
        """
        Get the transition history for a session.
        Args:
            session: Session object with state machine
        Returns:
            List of transition dictionaries
        """
        transitions = state_machine.get_session_history(session.id)
        return [t.to_dict() for t in transitions]


# Global transition handler instance


transition_handler = TransitionHandler()
