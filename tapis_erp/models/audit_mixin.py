import logging
from datetime import datetime

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

BLACKLIST_PATTERNS = [
    'write_date', 'create_date', 'create_uid', 'write_uid',
    '__last_update', 'display_name',
    'message_', 'activity_',
]


def _skip_field(fname):
    for p in BLACKLIST_PATTERNS:
        if p.endswith('_') and fname.startswith(p):
            return True
        if fname == p:
            return True
    return False


class TapisAuditMixin(models.AbstractModel):
    _name = 'tapis.audit.mixin'
    _description = 'Audit Mixin'

    def _audit_format(self, fname, value):
        if value is None or value is False:
            return ''
        field = self._fields.get(fname)
        if not field:
            return str(value)
        if field.type == 'boolean':
            return _('Yes') if value else _('No')
        if field.type == 'selection' and field.selection:
            sel = field.selection
            if callable(sel):
                sel = sel(self)
            labels = {v: l for v, l in sel}
            return labels.get(value, str(value))
        if field.type == 'many2one':
            if isinstance(value, models.BaseModel):
                return value.display_name or str(value.id)
            return str(value)
        if field.type == 'many2many':
            if isinstance(value, models.BaseModel):
                names = value.mapped('display_name')
                return ', '.join(names) if names else _('(none)')
            return str(value)
        if field.type == 'one2many':
            if isinstance(value, models.BaseModel):
                return _('%d item(s)') % len(value)
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        return str(value)

    def _audit_pick(self, fname):
        field = self._fields.get(fname)
        if not field:
            return False
        if not field.store:
            return False
        return True

    def _audit_read(self, fnames):
        result = {}
        for rec in self:
            vals = {}
            for fn in fnames:
                field = self._fields.get(fn)
                if not field:
                    continue
                try:
                    if field.type == 'many2one':
                        v = rec[fn]
                        vals[fn] = v.id if v else False
                    elif field.type in ('many2many', 'one2many'):
                        v = rec[fn]
                        vals[fn] = list(v.ids)
                    else:
                        vals[fn] = rec[fn]
                except Exception:
                    vals[fn] = _('<error>')
            result[rec.id] = vals
        return result

    def _audit_batch(self, entries):
        if not entries:
            return
        emp = self.env.user.employee_id
        eid = emp.id if emp else False
        common = {
            'user_id': self.env.user.id,
            'employee_id': eid,
        }
        batch = [{**common, **e} for e in entries]
        if batch:
            self.env['tapis.audit.log'].create(batch)

    def _audit_log_create(self):
        if self._context.get('skip_audit'):
            return
        fnames = [fn for fn in self._fields if not _skip_field(fn) and self._audit_pick(fn)]
        entries = []
        for fn in fnames:
            field = self._fields[fn]
            val = self._audit_format(fn, self[fn])
            if val:
                entries.append({
                    'name': _('Created %s') % self.display_name,
                    'model_name': self._name,
                    'record_id': self.id,
                    'record_name': self.display_name,
                    'action_type': 'create',
                    'field_name': fn,
                    'field_label': field.string or fn,
                    'new_value': val,
                    'description': _('Created %s') % self.display_name,
                })
        self._audit_batch(entries)

    def _audit_log_write(self, vals, old_values, new_values):
        if not vals or self._context.get('skip_audit'):
            return
        tracked = {k: v for k, v in vals.items() if not _skip_field(k)}
        if not tracked:
            return
        fnames = list(tracked.keys())
        entries = []
        for rec in self:
            rid = rec.id
            for fn in fnames:
                field = self._fields.get(fn)
                old_raw = old_values.get(rid, {}).get(fn)
                new_raw = new_values.get(rid, {}).get(fn)
                if not field:
                    continue
                label = field.string or fn
                old_fmt = self._audit_format(fn, old_raw)
                new_fmt = self._audit_format(fn, new_raw)
                if old_fmt == new_fmt:
                    continue
                entries.append({
                    'name': _('Updated %s - %s') % (rec.display_name, label),
                    'model_name': self._name,
                    'record_id': rid,
                    'record_name': rec.display_name,
                    'action_type': 'write',
                    'field_name': fn,
                    'field_label': label,
                    'old_value': old_fmt,
                    'new_value': new_fmt,
                    'description': _('Changed %s from "%s" to "%s"') % (
                        label, old_fmt, new_fmt
                    ),
                })
        self._audit_batch(entries)

    def _audit_log_unlink(self):
        if self._context.get('skip_audit'):
            return
        entries = []
        for rec in self:
            entries.append({
                'name': _('Deleted %s') % rec.display_name,
                'model_name': self._name,
                'record_id': rec.id,
                'record_name': rec.display_name,
                'action_type': 'unlink',
                'description': _('Deleted %s') % rec.display_name,
            })
        self._audit_batch(entries)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            try:
                rec._audit_log_create()
            except Exception:
                _logger.exception('Audit create failed: %s id=%d', rec._name, rec.id)
        return records

    def write(self, vals):
        if self._name == 'tapis.audit.log':
            return super().write(vals)
        try:
            tracked = {k: v for k, v in vals.items() if not _skip_field(k)}
            if tracked:
                old_values = self._audit_read(list(tracked.keys()))
            else:
                old_values = {}
            result = super().write(vals)
            if old_values:
                self.invalidate_cache(fnames=list(tracked.keys()))
                new_values = self._audit_read(list(tracked.keys()))
                self._audit_log_write(vals, old_values, new_values)
            return result
        except Exception:
            _logger.exception('Audit write failed for %s', self._name)
            return super().write(vals)

    def unlink(self):
        if self._name == 'tapis.audit.log':
            return super().unlink()
        try:
            self._audit_log_unlink()
        except Exception:
            _logger.exception('Audit unlink failed for %s', self._name)
        return super().unlink()
