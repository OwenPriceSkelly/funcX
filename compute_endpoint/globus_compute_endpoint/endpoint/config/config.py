from __future__ import annotations

import inspect
import os
import pathlib
import warnings

from globus_compute_endpoint.engines import GlobusComputeEngine
from parsl.utils import RepresentationMixin

_DEFAULT_EXECUTORS = [GlobusComputeEngine()]


class Config(RepresentationMixin):
    """Specification of Globus Compute configuration options.

    Parameters
    ----------

    executors : list of Executors
        A list of executors which serve as the backend for function execution.
        As of 0.2.2, this list should contain only one executor.
        Default: [GlobusComputeEngine()]

    environment: str
        Environment the endpoint should connect to. Sets funcx_service_address and
        results_ws_uri unless they are also specified. If not specified, the endpoint
        connects to production.
        Default: None

    funcx_service_address: str | None
        URL address string of the Globus Compute service to which the Endpoint
        should connect.
        Default: None

    results_ws_uri: str | None
        URL address string of the Globus Compute websocket service passed to the
        Globus Compute client.
        Default: None

    warn_about_url_mismatch: Bool
        Log a warning if funcx_service_address and results_ws_uri appear to point to
        different environments.
        Default: False

    heartbeat_period: int (seconds)
        The interval at which heartbeat messages are sent from the endpoint to the
        Globus Compute web service
        Default: 30s

    heartbeat_threshold: int (seconds)
        Seconds since the last hearbeat message from the Globus Compute web service
        after which the connection is assumed to be disconnected.
        Default: 120s

    idle_heartbeats_soft: int (count)
        Number of heartbeats after an endpoint is idle (no outstanding tasks or
        results, and at least 1 task or result has been forwarded) before the
        endpoint shuts down.  If 0, then the endpoint must be manually triggered
        to shut down (e.g., SIGINT or SIGTERM).
        Default: 0

    idle_heartbeats_hard: int (count)
        Number of heartbeats after no task or result has moved before the endpoint
        shuts down.  Unlike `idle_heartbeats_soft`, this idle timer does not require
        that there are no outstanding tasks or results.  If no task or result has
        moved in this many heartbeats, then the endpoint will shut down.  In
        particular, this is intended to catch the error condition that a worker
        has gone missing, and will thus _never_ return the task it was sent.
        Note that this setting is only enabled if the `idle_heartbeats_soft` is a
        value greater than 0.  Suggested value: a multiplier of heartbeat_period
        equivalent to two days.  For example, if `heartbeat_period` is 30s, then
        suggest 5760.
        Default: 5760

    stdout : str
        Path where the endpoint's stdout should be written
        Default: ./interchange.stdout

    stderr : str
        Path where the endpoint's stderr should be written
        Default: ./interchange.stderr

    detach_endpoint : Bool
        Should the endpoint deamon be run as a detached process? This is good for
        a real edge node, but an anti-pattern for kubernetes pods
        Default: True

    log_dir : str
        Optional path string to the top-level directory where logs should be written to.
        Default: None

    multi_user : bool | None
        Designates the endpoint as a multi-user endpoint
        Default: None

    allowed_functions : list[str] | None
        List of functions that are allowed to be run on the endpoint

    authentication_policy : str | None
        Endpoint users are evaluated against this Globus authentication policy

    subscription_id : str | None
        Subscription ID associated with this endpoint

    force_mu_allow_same_user : bool
        If set, override the heuristic that determines whether the uid running the
        multi-user endpoint may also run single-user endpoints.

        Normally, the multi-user endpoint disallows starting single-user endpoints with
        the same UID as the parent process unless the UID has no privileges.  That
        means that the UID is not 0 (root), or that the UID does *not* have (among
        many others) the capability to change the user (otherwise known as "drop
        privileges").

        Default: False

    display_name : str | None
        The display name for the endpoint.  If None, defaults to name
        Default: None

    endpoint_setup : str | None
        Command or commands to be run during the endpoint initialization process.

    endpoint_teardown : str | None
        Command or commands to be run during the endpoint shutdown process.

    mu_child_ep_grace_period_s : float
        If a single-user endpoint dies, and then the multi-user endpoint receives a
        start command for that single-user endpoint within this timeframe, the
        single-user endpoint is started back up again.
        Default: 30 seconds

    amqp_port : int | None
        Port to use for AMQP connections. Note that only 5671, 5672, and 443 are
        supported by the Compute web services. If None, the port is assigned by the
        services (typically 5671).
        Default: None
    """

    def __init__(
        self,
        # Execution backed
        executors: list = _DEFAULT_EXECUTORS,
        # Connection info
        environment: str | None = None,
        funcx_service_address=None,
        multi_user: bool | None = None,
        allowed_functions: list[str] | None = None,
        authentication_policy: str | None = None,
        subscription_id: str | None = None,
        amqp_port: int | None = None,
        # Tuning info
        heartbeat_period=30,
        heartbeat_threshold=120,
        identity_mapping_config_path: os.PathLike | None = None,
        idle_heartbeats_soft=0,
        idle_heartbeats_hard=5760,  # Two days, divided by `heartbeat_period`
        detach_endpoint=True,
        endpoint_setup: str | None = None,
        endpoint_teardown: str | None = None,
        force_mu_allow_same_user: bool = False,
        mu_child_ep_grace_period_s: float = 30,
        # Misc info
        display_name: str | None = None,
        # Logging info
        log_dir=None,
        stdout="./endpoint.log",
        stderr="./endpoint.log",
        **kwargs,
    ):
        for deprecated_name in ("results_ws_uri", "warn_about_url_mismatch"):
            if deprecated_name in kwargs:
                caller_filename = inspect.stack()[1].filename
                msg = (
                    f"The '{deprecated_name}' argument is deprecated.  It will"
                    f" be removed in a future release.  Found in: {caller_filename}"
                )
                warnings.warn(msg)
                del kwargs[deprecated_name]

        # A temporary measure; at some point in the near future, we'll split out
        # multi-user from single-user configs.  At that point, this particular stanza
        # will be incorporated more naturally into the multi-user handling.  Meanwhile,
        # `cqs_kwargs` and `rp_kwargs` are interfaces to internal class instantiations
        # for the multi-user endpoint; for now, I intend these to be "hidden" keys (or
        # at least not advertised, and will change, and will eat your cat if you touch
        # them).
        _internal = kwargs.pop("_internal", {})
        self._cqs_kwargs = _internal.pop("cqs_kwargs", None)
        self._rp_kwargs = _internal.pop("rp_kwargs", None)

        for unknown_arg in kwargs:
            # Calculated multiple times, but only in errant case -- nominally
            # fixed and then "not an issue."
            caller_filename = inspect.stack()[1].filename
            cls_name = self.__class__.__name__
            msg = (
                f"Unknown argument to {cls_name} ignored: {unknown_arg}"
                f"\n  Specified in: {caller_filename}"
            )
            warnings.warn(msg)

        # Execution backends
        self.executors = executors  # List of executors

        # Connection info
        self.environment = environment
        self.funcx_service_address = funcx_service_address

        # Multi-user tuning
        self.multi_user = multi_user is True
        self.force_mu_allow_same_user = force_mu_allow_same_user is True
        self.mu_child_ep_grace_period_s = mu_child_ep_grace_period_s
        self.identity_mapping_config_path = identity_mapping_config_path
        if self.identity_mapping_config_path:
            _p = pathlib.Path(self.identity_mapping_config_path)
            if not _p.exists():
                warnings.warn(f"Identity mapping config path not found ({_p})")

        # Auth
        self.allowed_functions = allowed_functions
        self.authentication_policy = authentication_policy
        self.subscription_id = subscription_id

        self.amqp_port = amqp_port

        # Single-user tuning
        self.heartbeat_period = heartbeat_period
        self.heartbeat_threshold = heartbeat_threshold
        self.idle_heartbeats_soft = int(max(0, idle_heartbeats_soft))
        self.idle_heartbeats_hard = int(max(0, idle_heartbeats_hard))
        self.detach_endpoint = detach_endpoint

        self.endpoint_setup = endpoint_setup
        self.endpoint_teardown = endpoint_teardown

        # Logging info
        self.log_dir = log_dir
        self.stdout = stdout
        self.stderr = stderr

        # Misc info
        self.display_name = display_name
