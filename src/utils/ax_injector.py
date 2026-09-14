"""macOS Accessibility API text injection via ApplicationServices.

Uses ctypes to call the ApplicationServices framework and directly
inject text into the focused UI element. This avoids clipboard
contamination but may fail in apps that don't expose their text
fields via the AX API (e.g., some Electron apps, terminals,
terminal emulators, certain web views).

When this fails, fall back to clipboard + Cmd+V injection.
"""

from __future__ import annotations

import ctypes
import logging
from ctypes import (
    CDLL,
    POINTER,
    byref,
    c_char_p,
    c_int,
    c_long,
    c_void_p,
)

logger = logging.getLogger("whisper")

# ── Load ApplicationServices framework ────────────────────────────────

# ApplicationServices is a meta-framework; the AX API lives in libAXAPI.dylib
# which is exposed through ApplicationServices. We load the meta-framework
# and resolve individual symbols.

# These are lazily initialized inside inject_via_ax_api() so that the
# module can be imported on non-macOS platforms without crashing.
_app_services: CDLL | None = None
_AxUIElementCreateSystemWide = None
_AxUIElementGetAttributeValue = None
_AxUIElementSetAttributeValue = None
_CFRelease = None
_CFStringCreateWithCharacters = None


def _ensure_loaded() -> CDLL:
    """Load ApplicationServices and resolve symbols on first call."""
    global _app_services  # noqa: PLW0603
    global _AxUIElementCreateSystemWide  # noqa: PLW0603
    global _AxUIElementGetAttributeValue  # noqa: PLW0603
    global _AxUIElementSetAttributeValue  # noqa: PLW0603
    global _CFRelease  # noqa: PLW0603
    global _CFStringCreateWithCharacters  # noqa: PLW0603
    if _app_services is not None:
        return _app_services
    _app_services = CDLL("ApplicationServices", mode=ctypes.RTLD_GLOBAL)
    _AxUIElementCreateSystemWide = _app_services.AXUIElementCreateSystemWide
    _AxUIElementCreateSystemWide.argtypes = [POINTER(AXUIElementRef)]
    _AxUIElementCreateSystemWide.restype = AXError

    _AxUIElementGetAttributeValue = _app_services.AXUIElementGetAttributeValue
    _AxUIElementGetAttributeValue.argtypes = [
        AXUIElementRef,
        CFStringRef,
        POINTER(c_void_p),
    ]
    _AxUIElementGetAttributeValue.restype = AXError

    _AxUIElementSetAttributeValue = _app_services.AXUIElementSetAttributeValue
    _AxUIElementSetAttributeValue.argtypes = [
        AXUIElementRef,
        CFStringRef,
        CFTypeRef,
    ]
    _AxUIElementSetAttributeValue.restype = AXError

    _CFRelease = _app_services.CFRelease
    _CFRelease.argtypes = [c_void_p]
    _CFRelease.restype = None

    _CFStringCreateWithCharacters = _app_services.CFStringCreateWithCharacters
    _CFStringCreateWithCharacters.argtypes = [
        c_void_p,
        c_char_p,
        c_long,
    ]
    _CFStringCreateWithCharacters.restype = CFStringRef
    return _app_services


# ── Type aliases ──────────────────────────────────────────────────────

# AXUIElementRef is an opaque pointer (void*).
AXUIElementRef = c_void_p

# AXError is a simple int enum (kAXErrorSuccess == 0).
AXError = c_int

# CoreFoundation types — we only need pointers for strings and values.
CFStringRef = c_void_p
CFTypeRef = c_void_p

# ── Constants ─────────────────────────────────────────────────────────

kAXErrorSuccess: int = 0
kAXErrorCannotComplete: int = -25207

# Attribute name strings (CFStringRef values).
_ATTR_FOCUSED_UI_ELEMENT = b"focusedUIElement"
_ATTR_SELECTED_TEXT = b"AXSelectedText"


def inject_via_ax_api(text: str) -> bool:
    """Try to inject text via macOS Accessibility API.

    Uses the ApplicationServices framework to directly set the
    AXSelectedText attribute of the focused UI element. This avoids
    clipboard contamination but may fail in apps that don't expose
    their text fields via the AX API (e.g., some Electron apps,
    terminals, certain web views).

    On failure (API unavailable, focused element doesn't support
    text injection, or permission denied), returns False gracefully
    — never raising an exception.

    Args:
        text: The text to inject into the focused application.

    Returns:
        True if injection succeeded, False if the API failed or
        the focused element doesn't support text injection.
    """
    try:
        # Ensure the framework is loaded (lazy, first-call only).
        _ensure_loaded()

        # Type-narrowing asserts so the type checker knows these are not None
        # after _ensure_loaded() has populated them via global assignment.
        assert _AxUIElementCreateSystemWide is not None
        assert _AxUIElementGetAttributeValue is not None
        assert _AxUIElementSetAttributeValue is not None
        assert _CFRelease is not None
        assert _CFStringCreateWithCharacters is not None

        # 1. Create a system-wide AXUIElement.
        system_element = AXUIElementRef()
        result = int(_AxUIElementCreateSystemWide(byref(system_element)))
        if result != kAXErrorSuccess:
            return False

        # 2. Get the focused UI element of the frontmost application.
        focused_element = c_void_p()
        result = int(
            _AxUIElementGetAttributeValue(
                system_element,
                _ATTR_FOCUSED_UI_ELEMENT,
                byref(focused_element),
            )
        )
        if result != kAXErrorSuccess or focused_element.value is None:
            return False

        # 3. Create a CFStringRef for the text we want to inject.
        text_bytes = text.encode("utf-8")
        text_cfstr = _CFStringCreateWithCharacters(
            c_void_p(0),  # NULL allocator (use default).
            text_bytes,
            c_long(len(text_bytes)),
        )
        if text_cfstr.value is None:
            return False

        # 4. Set the AXSelectedText attribute on the focused element.
        result = int(
            _AxUIElementSetAttributeValue(
                focused_element,
                _ATTR_SELECTED_TEXT,
                text_cfstr,
            )
        )

        # 5. Release the CFStringRef (memory management).
        _CFRelease(text_cfstr)

        # 6. Return success/failure.
        success = result == kAXErrorSuccess
        if not success:
            logger.debug(
                f"AX API injection failed with error code {result}. "
                "Falling back to clipboard+Cmd+V."
            )
        return success

    except Exception as e:
        logger.debug(f"AX API injection raised exception: {e}. Falling back.")
        return False
