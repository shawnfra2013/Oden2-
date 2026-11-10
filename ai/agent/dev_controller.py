import logging
from typing import Any

from .healthcheck import run_all_checks
from .proposal_builder import build as build_proposal

_logger = logging.getLogger(__name__)


class DevController:
    """
    A lightweight controller that delegates proposal creation to the existing
    `proposal_builder.build` function and performs health checks via
    `healthcheck.run_all_checks`. It does not instantiate any worker classes
    and is intended for use in development or testing environments.
    """

    def __init__(self, *, logger: logging.Logger = _logger) -> None:
        """
        Initialize the controller.

        Parameters
        ----------
        logger: logging.Logger
            Optional logger instance; defaults to module‑level logger.
        """
        self._logger = logger

    def create_proposal(self, name: str, task: str) -> Any:
        """
        Build a proposal using the shared `build_proposal` function.

        Parameters
        ----------
        name: str
            Identifier for the proposal.
        task: dict
            Task description that will be passed to the builder.

        Returns
        -------
        Any
            The constructed proposal object.
        """
        self._logger.debug("Creating proposal: name=%s, task=%s", name, task)
        try:
            proposal = build_proposal(name, task)
            self._logger.info("Proposal created successfully: %s", name)
            return proposal
        except Exception:  # pragma: no cover
            self._logger.exception("Failed to create proposal %s", name)
            raise

    def run_health_checks(self) -> list[dict]:
        """
        Execute all health checks using the shared `run_all_checks` function.

        Returns
        -------
        dict
            Mapping of check names to their results.
        """
        self._logger.debug("Running health checks")
        try:
            results = run_all_checks()
            self._logger.info("Health checks completed")
            return results
        except Exception:  # pragma: no cover
            self._logger.exception("Health checks failed")
            raise

    def handle_request(self, request: dict[str, Any]) -> Any:
        """
        Process a generic request dictionary. Expected keys:
        - ``action``: either ``"proposal"`` or ``"healthcheck"``.
        - ``name`` and ``task`` for proposal creation.
        - No additional data needed for health checks.

        Parameters
        ----------
        request: dict
            The incoming request payload.

        Returns
        -------
        Any
            The result of the requested action.
        """
        action = request.get("action")
        self._logger.debug("Handling request: %s", request)

        if action == "proposal":
            name = request.get("name")
            task = request.get("task", "")
            if not name:
                raise ValueError("Proposal request missing required 'name'")
            return self.create_proposal(name, task)

        if action == "healthcheck":
            return self.run_health_checks()

        raise ValueError(f"Unsupported action: {action}")


def get_dev_controller() -> DevController:
    """
    Return a ready‑to‑use ``DevController`` instance with default logging.
    """
    return DevController()
