"""Automatic audit logging hooks for SQLAlchemy session changes."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict

from flask import g
from sqlalchemy import event, inspect

from extensions.db import db
from models.audit_log import AuditLog


def _safe_value(val: Any) -> Any:
    """Convert values to JSON-safe representations."""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    # Fallback: string representation
    return str(val)


def _primary_key(obj) -> Any:
    insp = inspect(obj)
    pk_attrs = insp.mapper.primary_key
    values = {attr.key: getattr(obj, attr.key, None) for attr in pk_attrs}
    if len(values) == 1:
        return next(iter(values.values()))
    return values


def _changes_for_update(obj) -> Dict[str, Dict[str, Any]]:
    insp = inspect(obj)
    changes: Dict[str, Dict[str, Any]] = {}
    for attr in insp.attrs:
        hist = attr.history
        if hist.has_changes():
            old_val = hist.deleted[0] if hist.deleted else None
            new_val = hist.added[0] if hist.added else getattr(obj, attr.key, None)
            changes[attr.key] = {
                "old": _safe_value(old_val),
                "new": _safe_value(new_val),
            }
    return changes


def _should_skip(obj) -> bool:
    # Avoid auditing audit logs themselves or objects without mapper
    if isinstance(obj, AuditLog):
        return True
    try:
        inspect(obj)
    except Exception:
        return True
    return False


def register_audit_listeners():
    """Attach after_flush listeners once."""
    if getattr(register_audit_listeners, "_registered", False):
        return

    @event.listens_for(db.session, "after_flush")
    def _audit_after_flush(session, flush_context):
        user_id = getattr(g, "current_user_id", None)

        # New objects
        for obj in list(session.new):
            if _should_skip(obj):
                continue
            try:
                log = AuditLog(
                    entity_type=getattr(obj, "__tablename__", obj.__class__.__name__),
                    entity_id=_primary_key(obj),
                    action="create",
                    user_id=user_id,
                    changes=None,
                )
                session.add(log)
            except Exception:
                continue

        # Updated objects
        for obj in list(session.dirty):
            if _should_skip(obj):
                continue
            try:
                if not session.is_modified(obj, include_collections=False):
                    continue
                changes = _changes_for_update(obj)
                if not changes:
                    continue
                log = AuditLog(
                    entity_type=getattr(obj, "__tablename__", obj.__class__.__name__),
                    entity_id=_primary_key(obj),
                    action="update",
                    user_id=user_id,
                    changes=changes,
                )
                session.add(log)
            except Exception:
                continue

        # Deleted objects
        for obj in list(session.deleted):
            if _should_skip(obj):
                continue
            try:
                log = AuditLog(
                    entity_type=getattr(obj, "__tablename__", obj.__class__.__name__),
                    entity_id=_primary_key(obj),
                    action="delete",
                    user_id=user_id,
                    changes=None,
                )
                session.add(log)
            except Exception:
                continue

    register_audit_listeners._registered = True
