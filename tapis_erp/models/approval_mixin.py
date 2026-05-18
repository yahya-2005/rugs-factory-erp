from odoo import _, models, fields, api


class TapisApprovalMixin(models.AbstractModel):
    _name = 'tapis.approval.mixin'
    _description = 'Approval Mixin'

    approval_request_id = fields.Many2one('tapis.approval.request', string='Approval Request', readonly=True, copy=False)
    approval_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', compute='_compute_approval_state', store=False)

    @api.depends('approval_request_id', 'approval_request_id.state')
    def _compute_approval_state(self):
        for rec in self:
            if rec.approval_request_id:
                mapping = {
                    'draft': 'not_required',
                    'pending': 'pending',
                    'approved': 'approved',
                    'rejected': 'rejected',
                    'cancelled': 'not_required',
                }
                rec.approval_state = mapping.get(rec.approval_request_id.state, 'not_required')
            else:
                rec.approval_state = 'not_required'

    def action_request_approval(self):
        self.ensure_one()
        amount = self._get_approval_amount()
        category_code = self._get_approval_category_code()
        cost_center = self._get_approval_cost_center()
        category = self.env['tapis.approval.category'].search([('code', '=', category_code)], limit=1)
        if not category:
            raise UserError(_('No approval category found for code: %s') % category_code)
        existing = self.env['tapis.approval.request'].search([
            ('reference_model', '=', self._name),
            ('reference_id', '=', self.id),
            ('state', 'in', ('draft', 'pending')),
        ], limit=1)
        if existing:
            raise UserError(_('An approval request already exists for this record.'))
        request = self.env['tapis.approval.request'].create({
            'category_id': category.id,
            'reference_model': self._name,
            'reference_id': self.id,
            'amount': amount,
            'cost_center_id': cost_center.id if cost_center else False,
        })
        request.action_submit()
        self.approval_request_id = request.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approval Request',
            'res_model': 'tapis.approval.request',
            'view_mode': 'form',
            'res_id': request.id,
            'target': 'current',
        }

    def action_open_approval_request(self):
        self.ensure_one()
        if not self.approval_request_id:
            raise UserError(_('No approval request linked to this record.'))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approval Request',
            'res_model': 'tapis.approval.request',
            'view_mode': 'form',
            'res_id': self.approval_request_id.id,
            'target': 'current',
        }

    def _get_approval_amount(self):
        return 0.0

    def _get_approval_category_code(self):
        return ''

    def _get_approval_cost_center(self):
        return False

    def _on_approval_approved(self):
        pass

    def _on_approval_rejected(self):
        pass
