"""
Observability helpers that sit on top of the VM controller client.

This module centralises state inspection routines (screenshot capture,
clipboard reads, cursor position, etc.) needed by the orchestrator when
constructing user-facing payloads.
"""

from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from framework.api.controller_client import VMControllerClient, VMControllerError
from framework.utils.image_processor import ImageProcessor, downscale_image_bytes


def _parse_active_context_from_at(at_xml: str) -> Dict[str, Any]:
    """
    Parse active window/application/url details from an accessibility tree XML string.
    """
    context: Dict[str, Any] = {
        "active_window": None,
        "active_application": None,
        "active_url": None,
        "meta": {},
    }
    if not at_xml:
        return context

    try:
        import lxml.etree as etree  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        context["meta"]["lxml_error"] = str(exc)
        return context

    try:
        root = etree.fromstring(at_xml.encode("utf-8"))
    except Exception as exc:
        context["meta"]["parse_error"] = str(exc)
        return context

    nsmap = {k: v for k, v in (root.nsmap or {}).items() if k}
    state_ns = nsmap.get("st") or next(
        (uri for uri in nsmap.values() if uri.endswith("/ns/state")), None
    )
    attr_ns = nsmap.get("attr") or next(
        (uri for uri in nsmap.values() if uri.endswith("/ns/attributes")), None
    )
    doc_ns = nsmap.get("doc")

    namespaces: Dict[str, str] = {}
    if state_ns:
        namespaces["st"] = state_ns
    if attr_ns:
        namespaces["attr"] = attr_ns
    if doc_ns:
        namespaces["doc"] = doc_ns

    context["meta"]["accessibility_ns"] = {k: v for k, v in namespaces.items()}
    context["meta"]["tree_length"] = len(at_xml)

    active_node = None
    if "st" in namespaces:
        for xpath in (
            '//frame[@st:active="true"]',
            '//application[@st:active="true"]',
            '//*[@st:active="true"]',
        ):
            nodes = root.xpath(xpath, namespaces=namespaces)
            if nodes:
                active_node = nodes[0]
                context["meta"]["active_node_xpath"] = xpath
                break
    if active_node is None:
        return context

    window_name = (active_node.get("name") or "").strip()
    application_name = ""
    parent = active_node.getparent()
    while parent is not None and not application_name:
        candidate = (parent.get("name") or "").strip()
        if candidate:
            application_name = candidate
            break
        parent = parent.getparent()

    if window_name and application_name and application_name.lower() not in window_name.lower():
        combined = f"{application_name} - {window_name}".strip(" -")
    else:
        combined = window_name or application_name

    if combined:
        context["active_window"] = combined
    if application_name:
        context["active_application"] = application_name
    elif window_name:
        context["active_application"] = window_name
    elif combined:
        context["active_application"] = combined

    if "st" in namespaces:
        for xpath in (
            '//document[@st:focused="true"]',
            '//webarea[@st:focused="true"]',
            '//frame[@st:focused="true"]',
        ):
            nodes = root.xpath(xpath, namespaces=namespaces)
            for node in nodes:
                url_value = None
                if attr_ns:
                    url_value = node.get(f"{{{attr_ns}}}url")
                if not url_value:
                    url_value = node.get("url")
                if url_value:
                    context["active_url"] = url_value
                    context["meta"]["active_url_source"] = xpath
                    break
            if context["active_url"]:
                break

    return context


@dataclass
class ObservationSnapshot:
    """
    Container for a single VM observation.

    Attributes capture both raw state (clipboard, cursor) and derived metadata
    that the orchestrator can embed into user prompts.
    """

    platform: Optional[str] = None
    clipboard: Optional[str] = None
    cursor_position: Optional[Tuple[int, int]] = None
    terminal_output: Optional[str] = None
    screen_size: Optional[Dict[str, Any]] = None
    active_window: Optional[str] = None
    active_application: Optional[str] = None
    active_url: Optional[str] = None  # Typically unavailable without extra instrumentation
    screenshot_path: Optional[Path] = None
    screenshot_b64: Optional[str] = None
    timestamp: float = field(default_factory=lambda: time.time())
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self, *, include_screenshot: bool = True) -> Dict[str, Any]:
        """
        Flatten the snapshot into a JSON-serialisable payload suitable for the orchestrator.
        """
        payload: Dict[str, Any] = {
            "timestamp": self.timestamp,
            "platform": self.platform,
            "clipboard": self.clipboard,
            "cursor_position": list(self.cursor_position) if self.cursor_position else None,
            "terminal_output": self.terminal_output,
            "screen_size": self.screen_size,
            "active_window": self.active_window,
            "active_application": self.active_application,
            "active_url": self.active_url,
        }
        if include_screenshot and self.screenshot_b64:
            payload["screenshot_b64"] = self.screenshot_b64
        if include_screenshot and self.screenshot_path:
            payload["screenshot_path"] = str(self.screenshot_path)
        if self.raw_metadata:
            payload["meta"] = self.raw_metadata
        return payload


class VMObserver:
    """
    High-level observability facade built on top of `VMControllerClient`.

    Responsibilities:
        * expose explicit helpers (clipboard, screenshot, cursor position, etc.)
        * aggregate observations into `ObservationSnapshot` instances
        * construct orchestrator payloads with sensible defaults
    """

    def __init__(
        self,
        client: Optional[VMControllerClient] = None,
        *,
        screenshot_dir: Optional[Union[str, Path]] = None,
        client_kwargs: Optional[Dict[str, Any]] = None,
        image_processor: Optional[ImageProcessor] = None,
    ) -> None:
        self._client = client or VMControllerClient(**(client_kwargs or {}))
        self._image_processor = image_processor or ImageProcessor()
        self._latest_screenshot_hash: Optional[int] = None
        if screenshot_dir:
            target = Path(screenshot_dir).expanduser()
            target.mkdir(parents=True, exist_ok=True)
            self._screenshot_dir = target
        else:
            self._screenshot_dir = Path(tempfile.gettempdir())

    # ------------------------------------------------------------------ #
    # Direct accessors
    # ------------------------------------------------------------------ #

    def capture_screenshot(
        self,
        *,
        filename: Optional[str] = None,
        encode_base64: bool = True,
        downscale: bool = False,
        max_width: int = 1280,
        max_height: int = 720,
    ) -> Tuple[Path, Optional[str]]:
        """
        Capture a screenshot and persist it locally. Returns the path and optional base64 string.
        """
        snapshot_bytes = self._client.capture_screenshot()
        self._latest_screenshot_hash = None
        if downscale:
            snapshot_bytes = downscale_image_bytes(
                snapshot_bytes, max_w=max_width, max_h=max_height
            )
        filename = filename or f"vm_screenshot_{int(time.time() * 1000)}.png"
        destination = self._screenshot_dir / filename
        destination.write_bytes(snapshot_bytes)

        b64_value = None
        if encode_base64:
            b64_value = self._image_processor.encode_image(snapshot_bytes)
            snapshot_hash = self._image_processor.dhash(snapshot_bytes)
            self._latest_screenshot_hash = snapshot_hash
        return destination, b64_value

    def clipboard(self) -> Optional[str]:
        """
        Fetch the clipboard contents (best-effort).
        """
        response = self._client.clipboard()
        if isinstance(response, dict) and response.get("status") == "success":
            return response.get("clipboard")
        return None

    def cursor_position(self) -> Optional[Tuple[int, int]]:
        """
        Return the cursor position (x, y) when available.
        """
        try:
            coords = self._client.cursor_position()
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                return int(coords[0]), int(coords[1])
        except VMControllerError:
            pass
        return None

    def terminal_output(self) -> Optional[str]:
        """
        Retrieve a snapshot of the terminal output (Linux only in the current server implementation).
        """
        try:
            response = self._client.terminal_output()
        except VMControllerError:
            return None
        if isinstance(response, dict) and response.get("status") == "success":
            return response.get("output")
        return None

    def platform(self) -> Optional[str]:
        """
        Return the platform string reported by the controller.
        """
        try:
            return self._client.get_platform().strip()
        except VMControllerError:
            return None

    def screen_size(self) -> Optional[Dict[str, Any]]:
        """
        Return screen geometry when available.
        """
        try:
            return self._client.screen_size()
        except VMControllerError:
            return None

    # ------------------------------------------------------------------ #
    # Aggregated state
    # ------------------------------------------------------------------ #

    def snapshot(
        self,
        *,
        include_screenshot: bool = True,
        encode_screenshot: bool = True,
    ) -> ObservationSnapshot:
        """
        Collect a best-effort snapshot of the VM state.
        """
        snapshot = ObservationSnapshot()
        snapshot.platform = self.platform()
        snapshot.cursor_position = self.cursor_position()
        clipboard_response = self._safe_call(self._client.clipboard, default=None)
        if isinstance(clipboard_response, dict):
            if clipboard_response.get("status") == "success":
                snapshot.clipboard = clipboard_response.get("clipboard")
            snapshot.raw_metadata["clipboard_response"] = clipboard_response

        terminal_response = self._safe_call(self._client.terminal_output, default=None)
        if isinstance(terminal_response, dict):
            if terminal_response.get("status") == "success":
                snapshot.terminal_output = terminal_response.get("output")
            snapshot.raw_metadata["terminal_response"] = terminal_response

        snapshot.screen_size = self.screen_size()

        context = self._collect_active_context(snapshot.platform)
        snapshot.active_window = context.get("active_window")
        snapshot.active_application = context.get("active_application")
        snapshot.active_url = context.get("active_url")
        if context.get("meta"):
            snapshot.raw_metadata["active_context"] = context["meta"]

        desktop_info = self._safe_call(self._client.desktop_path, default=None)
        if desktop_info:
            snapshot.raw_metadata["desktop_path"] = desktop_info

        if include_screenshot:
            try:
                path, encoded = self.capture_screenshot(
                    encode_base64=encode_screenshot,
                    downscale=False,
                )
                snapshot.screenshot_path = path
                snapshot.screenshot_b64 = encoded
                if encoded and self._latest_screenshot_hash is not None:
                    snapshot.raw_metadata["screenshot_hash"] = self._latest_screenshot_hash
            except VMControllerError as exc:
                snapshot.raw_metadata["screenshot_error"] = str(exc)

        return snapshot

    def build_user_payload(self, *, include_screenshot: bool = True) -> Dict[str, Any]:
        """
        Produce a user payload dictionary ready for prompt assembly.
        """
        snapshot = self.snapshot(include_screenshot=include_screenshot, encode_screenshot=include_screenshot)
        return snapshot.to_payload(include_screenshot=include_screenshot)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _collect_active_context(self, platform_name: Optional[str]) -> Dict[str, Any]:
        """
        Attempt to collect foreground window/application information.

        Pulls the accessibility tree from the controller and infers
        foreground context. Falls back gracefully when the accessibility
        information is unavailable or cannot be parsed.
        """
        context: Dict[str, Any] = {
            "active_window": None,
            "active_application": None,
            "active_url": None,
            "meta": {"requested_platform": platform_name},
        }

        tree_response = self._safe_call(self._client.accessibility_tree, default=None)
        at_xml: Optional[str] = None

        if isinstance(tree_response, dict):
            if "AT" in tree_response:
                at_xml = tree_response.get("AT")
            elif "at" in tree_response:
                at_xml = tree_response.get("at")
            if "error" in tree_response and not at_xml:
                context["meta"]["accessibility_error"] = tree_response
            else:
                keys = [k for k in tree_response.keys() if k.upper() != "AT"]
                if keys:
                    context["meta"]["accessibility_response_keys"] = keys
        elif isinstance(tree_response, str):
            at_xml = tree_response
        elif tree_response is not None:
            context["meta"]["accessibility_response_type"] = type(tree_response).__name__

        if at_xml:
            parsed = _parse_active_context_from_at(at_xml)
            for key in ("active_window", "active_application", "active_url"):
                if parsed.get(key):
                    context[key] = parsed[key]
            context_meta = parsed.get("meta") or {}
            context["meta"].update(context_meta)
            context["meta"]["accessibility_tree_available"] = True
        else:
            context["meta"]["accessibility_tree_available"] = False

        return context

    def _safe_call(self, func, default: Any = None) -> Any:
        try:
            return func()
        except VMControllerError as exc:
            return {
                "error": str(exc),
                "status_code": exc.status_code,
                "payload": exc.payload,
            }
        except Exception:
            return default

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "VMObserver":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
