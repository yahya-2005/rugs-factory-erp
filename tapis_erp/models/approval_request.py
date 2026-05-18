from odoo import _, models, fields, api
from odoo.exceptions import UserError
from datetime import datetime


class TapisApprovalRequest(models.Model):
    _name = 'tapis.approval.request'
    _description = 'Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.audit.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default=lambda s: _('New'), tracking=True)
    category_id = fields.Many2one('tapis.approval.category', string='Category', required=True, tracking=True)
    reference_model = fields.Char(string='Reference Model', required=True, help="Technical model name of the referenced record")
    reference_id = fields.Integer(string='Reference ID', required=True, help="ID of the referenced record")
    reference_display = fields.Char(string='Reference', compute='_compute_reference_display', store=False)

    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user, required=True, tracking=True)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, required=True, tracking=True)

    amount = fields.Float(string='Amount', default=0.0, help="Monetary value for rule matching")
    cost_center_id = fields.Many2one('tapis.cost.center', string='Cost Center')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    line_ids = fields.One2many('tapis.approval.request.line', 'request_id', string='Approval Lines')

    current_sequence = fields.Integer(string='Current Sequence', default=0, help="Tracks which sequential level is active")
    total_required = fields.Integer(string='Total Required', compute='_compute_progress', store=True)
    total_approved = fields.Integer(string='Total Approved', compute='_compute_progress', store=True)
    progress_percent = fields.Float(string='Progress %', compute='_compute_progress', store=True)

    @api.depends('reference_model', 'reference_id')
    def _compute_reference_display(self):
        for rec in self:
            if rec.reference_model and rec.reference_id:
                try:
                    model = self.env[rec.reference_model]
                    record = model.browse(rec.reference_id)
                    rec.reference_display = record.display_name if record else f"{rec.reference_model}: {rec.reference_id}"
                except Exception:
                    rec.reference_display = f"{rec.reference_model}: {rec.reference_id}"
            else:
                rec.reference_display = False

    @api.depends('line_ids', 'line_ids.state')
    def _compute_progress(self):
        for rec in self:
            rec.total_required = len(rec.line_ids)
            rec.total_approved = len(rec.line_ids.filtered(lambda l: l.state == 'approved'))
            rec.progress_percent = (rec.total_approved / rec.total_required * 100) if rec.total_required else 0.0

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            rec._generate_approval_lines()
            rec.state = 'pending'
            rec.message_post(body=_('Approval request submitted.'))
            rec._notify_approvers()

    def _generate_approval_lines(self):
        self.ensure_one()
        existing = self.line_ids
        if existing:
            existing.unlink()
        rules = self._get_matching_rules()
        sequence = 1
        for rule in rules:
            for user in rule.approver_user_ids:
                self.env['tapis.approval.request.line'].create({
                    'request_id': self.id,
                    'rule_id': rule.id,
                    'sequence': sequence,
                    'approver_id': user.id,
                    'state': 'pending',
                })
            sequence += 1

    def _get_matching_rules(self):
        self.ensure_one()
        domain = [
            ('category_id', '=', self.category_id.id),
            ('active', '=', True),
        ]
        amount = self.amount or 0.0
        rules = self.env['tapis.approval.rule'].search(domain, order='sequence, id')
        matching = rules.filtered(lambda r:
            amount >= r.min_amount and
            (r.max_amount == 0 or amount <= r.max_amount) and
            (not r.cost_center_id or r.cost_center_id == self.cost_center_id)
        )
        return matching

    def _notify_approvers(self):
        for line in self.line_ids.filtered(lambda l: l.state == 'pending'):
            line.approver_id.notify_dispatch(message='Approval request %s requires your action.' % self.name)

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending requests can be approved.'))
        current_line = self._get_current_line()
        if not current_line:
            raise UserError(_('No pending approval lines found.'))
        if self.env.user not in current_line.rule_id.approver_user_ids:
            raise UserError(_('You are not authorized to approve this request.'))
        current_line.write({
            'state': 'approved',
            'decision_date': fields.Datetime.now(),
            'comment': False,
        })
        self.message_post(body=_('Line %s approved by %s.') % (current_line.sequence, self.env.user.name))
        if self._check_full_approval():
            self.state = 'approved'
            self.message_post(body=_('Approval request fully approved.'))
            self._trigger_approval_callback()

    def _get_current_line(self):
        self.ensure_one()
        rule = self._get_current_rule()
        if not rule:
            return False
        if rule.is_sequential:
            pending = self.line_ids.filtered(lambda l: l.state == 'pending' and l.rule_id == rule)
            return pending[:1] if pending else False
        else:
            pending = self.line_ids.filtered(lambda l: l.state == 'pending' and l.rule_id == rule)
            if not pending:
                return False
            approved = self.line_ids.filtered(lambda l: l.state == 'approved' and l.rule_id == rule)
            if len(approved) < rule.required_approvals and self.env.user in pending.mapped('approver_id'):
                return pending.filtered(lambda l: l.approver_id == self.env.user)[:1]
            return False

    def _get_current_rule(self):
        self.ensure_one()
        rules = self._get_matching_rules()
        if not rules:
            return False
        done_sequences = self.line_ids.filtered(lambda l: l.state in ('approved', 'rejected', 'skipped')).mapped('sequence')
        if done_sequences:
            max_done = max(done_sequences)
            remaining = rules.filtered(lambda r: r.sequence > max_done)
            return remaining[:1] if remaining else False
        return rules[:1]

    def _check_full_approval(self):
        self.ensure_one()
        for line in self.line_ids:
            if line.state == 'pending':
                return False
        return True

    def _trigger_approval_callback(self):
        self.ensure_one()
        try:
            model = self.env[self.reference_model]
            record = model.browse(self.reference_id)
            if record and hasattr(record, '_on_approval_approved'):
                record._on_approval_approved()
        except Exception:
            pass

    def action_reject(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending requests can be rejected.'))
        current_line = self._get_current_line()
        if not current_line:
            raise UserError(_('No pending approval lines found.'))
        if self.env.user not in current_line.rule_id.approver_user_ids:
            raise UserError(_('You are not authorized to reject this request.'))
        current_line.write({
            'state': 'rejected',
            'decision_date': fields.Datetime.now(),
            'comment': False,
        })
        self.state = 'rejected'
        self.message_post(body=_('Approval request rejected by %s.') % self.env.user.name)
        self._trigger_rejection_callback()

    def _trigger_rejection_callback(self):
        self.ensure_one()
        try:
            model = self.env[self.reference_model]
            record = model.browse(self.reference_id)
            if record and hasattr(record, '_on_approval_rejected'):
                record._on_approval_rejected()
        except Exception:
            pass

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'pending'):
                raise UserError(_('Only draft or pending requests can be cancelled.'))
            rec.state = 'cancelled'
            rec.message_post(body=_('Approval request cancelled.'))

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tapis.approval.request.code') or _('New')
        return super().create(vals)

    def action_open_reference(self):
        self.ensure_one()
        if not self.reference_model or not self.reference_id:
            raise UserError(_('No reference record found.'))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reference',
            'res_model': self.reference_model,
            'view_mode': 'form',
            'res_id': self.reference_id,
            'target': 'current',
        }


class TapisApprovalRequestLine(models.Model):
    _name = 'tapis.approval.request.line'
    _description = 'Approval Request Line'
    _order = 'sequence, id'

    request_id = fields.Many2one('tapis.approval.request', string='Approval Request', required=True, ondelete='cascade')
    rule_id = fields.Many2one('tapis.approval.rule', string='Rule', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    approver_id = fields.Many2one('res.users', string='Approver', required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
    ], string='Status', default='pending', required=True)
    decision_date = fields.Datetime(string='Decision Date')
    comment = fields.Text(string='Comment')
