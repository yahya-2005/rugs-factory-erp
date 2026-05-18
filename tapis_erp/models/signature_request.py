from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TapisSignatureRequest(models.Model):
    _name = 'tapis.signature.request'
    _description = 'Signature Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', default=lambda s: _('New'), readonly=True, tracking=True)
    template_id = fields.Many2one('tapis.signature.template', string='Template', required=True)
    reference_model = fields.Char(required=True)
    reference_id = fields.Integer(required=True)
    reference_display = fields.Char(compute='_compute_reference_display', store=True)

    requested_by_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user, required=True, tracking=True)
    request_date = fields.Datetime(string='Date', default=fields.Datetime.now, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('signed', 'Signed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    progress_percent = fields.Integer(compute='_compute_progress', store=True)
    total_signers = fields.Integer(compute='_compute_progress', store=True)
    signed_count = fields.Integer(compute='_compute_progress', store=True)

    line_ids = fields.One2many('tapis.signature.request.line', 'request_id', string='Signers')

    @api.depends('reference_model', 'reference_id')
    def _compute_reference_display(self):
        for rec in self:
            if rec.reference_model and rec.reference_id:
                model = self.env.get(rec.reference_model)
                if model:
                    record = model.browse(rec.reference_id)
                    rec.reference_display = record.display_name
                else:
                    rec.reference_display = '%s #%d' % (rec.reference_model, rec.reference_id)
            else:
                rec.reference_display = False

    @api.depends('line_ids.state')
    def _compute_progress(self):
        for rec in self:
            total = len(rec.line_ids)
            signed = len(rec.line_ids.filtered(lambda l: l.state == 'signed'))
            rec.total_signers = total
            rec.signed_count = signed
            rec.progress_percent = round(signed / total * 100) if total else 0

    def _generate_lines(self):
        self.ensure_one()
        existing = self.env['tapis.signature.request.line'].search([('request_id', '=', self.id)])
        if existing:
            return
        roles = self.template_id.signer_role_ids.sorted('sequence')
        lines = []
        for role in roles:
            users = role.user_ids
            if not users:
                users = self.requested_by_id
            for user in users:
                lines.append({
                    'request_id': self.id,
                    'role_id': role.id,
                    'sequence': role.sequence,
                    'signer_id': user.id,
                })
        if lines:
            self.env['tapis.signature.request.line'].create(lines)

    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            self._generate_lines()
        if not self.line_ids:
            raise UserError(_('No signers configured for this template.'))
        self.state = 'pending'
        first_lines = self.line_ids.sorted('sequence')
        for line in first_lines.filtered(lambda l: l.sequence == first_lines[0].sequence):
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('Signature Required: %s') % self.name,
                'note': _('You have been requested to sign: %s') % self.reference_display,
                'user_id': line.signer_id.id,
                'res_model_id': self.env['ir.model']._get_id('tapis.signature.request'),
                'res_id': self.id,
            })

    def action_sign(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending requests can be signed.'))
        current_line = self.line_ids.filtered(
            lambda l: l.signer_id.id == self.env.user.id and l.state == 'pending'
        )
        if not current_line:
            raise UserError(_('You do not have a pending signature line on this request.'))
        if not current_line.signature_image:
            raise UserError(_('Please provide your signature image before signing.'))
        current_line.write({
            'state': 'signed',
            'signed_date': fields.Datetime.now(),
            'signer_ip': self.env.request.httprequest.remote_addr if self.env.request else False,
            'signer_user_agent': self.env.request.httprequest.user_agent.string if self.env.request else False,
        })
        remaining = self.line_ids.filtered(lambda l: l.state == 'pending')
        if not remaining:
            self.state = 'signed'
            self._notify_complete()
            if self.template_id.auto_complete_record:
                self._trigger_record_callback('_on_signature_completed')
        else:
            next_lines = remaining.sorted('sequence')
            next_seq = next_lines[0].sequence
            for line in next_lines.filtered(lambda l: l.sequence == next_seq):
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': _('Signature Required: %s') % self.name,
                    'note': _('You have been requested to sign: %s') % self.reference_display,
                    'user_id': line.signer_id.id,
                    'res_model_id': self.env['ir.model']._get_id('tapis.signature.request'),
                    'res_id': self.id,
                })

    def action_reject(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending requests can be rejected.'))
        current_line = self.line_ids.filtered(
            lambda l: l.signer_id.id == self.env.user.id and l.state == 'pending'
        )
        if not current_line:
            raise UserError(_('You do not have a pending signature line on this request.'))
        current_line.write({
            'state': 'rejected',
            'signed_date': fields.Datetime.now(),
            'signer_ip': self.env.request.httprequest.remote_addr if self.env.request else False,
            'signer_user_agent': self.env.request.httprequest.user_agent.string if self.env.request else False,
        })
        self.state = 'rejected'
        self._notify_reject()
        self._trigger_record_callback('_on_signature_rejected')

    def action_cancel(self):
        self.ensure_one()
        if self.state in ('signed', 'cancelled'):
            raise UserError(_('Cannot cancel a signed or already cancelled request.'))
        self.state = 'cancelled'

    def action_open_reference(self):
        self.ensure_one()
        model = self.env.get(self.reference_model)
        if not model:
            raise UserError(_('Reference model not found: %s') % self.reference_model)
        record = model.browse(self.reference_id)
        if not record.exists():
            raise UserError(_('Reference record not found.'))
        return {
            'type': 'ir.actions.act_window',
            'name': record.display_name,
            'res_model': self.reference_model,
            'res_id': self.reference_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _notify_complete(self):
        self.message_post(
            body=_('All signatures have been collected for %s.') % self.reference_display,
            subject=_('Signature Complete'),
        )

    def _notify_reject(self):
        self.message_post(
            body=_('Signature request was rejected by %s.') % self.env.user.name,
            subject=_('Signature Rejected'),
        )

    def _trigger_record_callback(self, callback_name):
        self.ensure_one()
        model = self.env.get(self.reference_model)
        if not model:
            return
        record = model.browse(self.reference_id)
        if record.exists() and hasattr(record, callback_name):
            getattr(record, callback_name)()

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tapis.signature.request') or _('New')
        return super().create(vals)


class TapisSignatureRequestLine(models.Model):
    _name = 'tapis.signature.request.line'
    _description = 'Signature Request Line'
    _order = 'sequence, id'

    request_id = fields.Many2one('tapis.signature.request', string='Request', required=True, ondelete='cascade')
    role_id = fields.Many2one('tapis.signature.role', string='Role')
    sequence = fields.Integer(default=10)
    signer_id = fields.Many2one('res.users', string='Signer', required=True)

    state = fields.Selection([
        ('pending', 'Pending'),
        ('signed', 'Signed'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
    ], string='Status', default='pending', required=True)

    signature_image = fields.Binary(string='Signature', attachment=True)
    signed_date = fields.Datetime(string='Signed Date')
    signer_comment = fields.Text(string='Comment')
    signer_ip = fields.Char(string='IP Address')
    signer_user_agent = fields.Text(string='User Agent')
