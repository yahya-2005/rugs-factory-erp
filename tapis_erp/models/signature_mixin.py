from odoo import _, api, fields, models


class TapisSignatureMixin(models.AbstractModel):
    _name = 'tapis.signature.mixin'
    _description = 'Signature Mixin'

    signature_request_id = fields.Many2one('tapis.signature.request', string='Signature Request', readonly=True, copy=False)
    signature_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('signed', 'Signed'),
        ('rejected', 'Rejected'),
    ], string='Signature Status', compute='_compute_signature_state', store=True, default='not_required')

    @api.depends('signature_request_id', 'signature_request_id.state')
    def _compute_signature_state(self):
        for rec in self:
            if not rec.signature_request_id:
                rec.signature_state = 'not_required'
            elif rec.signature_request_id.state == 'pending':
                rec.signature_state = 'pending'
            elif rec.signature_request_id.state == 'signed':
                rec.signature_state = 'signed'
            elif rec.signature_request_id.state == 'rejected':
                rec.signature_state = 'rejected'
            else:
                rec.signature_state = 'not_required'

    def action_request_signature(self):
        self.ensure_one()
        template_code = self._get_signature_template_code()
        if not template_code:
            raise UserError(_('No signature template configured for this document type.'))
        template = self.env['tapis.signature.template'].search([
            ('code', '=', template_code),
            ('active', '=', True),
        ], limit=1)
        if not template:
            raise UserError(_('Signature template "%s" not found.') % template_code)
        request = self.env['tapis.signature.request'].create({
            'template_id': template.id,
            'reference_model': self._name,
            'reference_id': self.id,
            'requested_by_id': self.env.user.id,
        })
        request.action_submit()
        self.signature_request_id = request.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Signature Request'),
            'res_model': 'tapis.signature.request',
            'res_id': request.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_signature_request(self):
        self.ensure_one()
        if not self.signature_request_id:
            raise UserError(_('No signature request found for this record.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Signature Request'),
            'res_model': 'tapis.signature.request',
            'res_id': self.signature_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_signature_template_code(self):
        return None

    def _on_signature_completed(self):
        pass

    def _on_signature_rejected(self):
        pass
