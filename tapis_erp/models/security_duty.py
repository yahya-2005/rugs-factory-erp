from odoo import models, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'tapis.purchase'

    def action_approve(self):
        for rec in self:
            if rec.create_uid.id == self.env.user.id:
                self.env['tapis.security.incident'].create({
                    'name': _('Segregation of Duties: Self-approval on Purchase %s') % rec.name,
                    'user_id': self.env.user.id,
                    'model_name': 'tapis.purchase',
                    'operation': 'self_approve',
                    'description': _('User %s attempted to approve their own purchase order %s.') % (self.env.user.name, rec.name),
                    'severity': 'high',
                })
                raise UserError(_(
                    'Segregation of Duties Violation: You cannot approve a purchase order that you created. '
                    'This must be approved by another authorized user.'
                ))
        return super(PurchaseOrder, self).action_approve()


class Budget(models.Model):
    _inherit = 'tapis.budget'

    def action_confirm(self):
        for rec in self:
            if rec.create_uid.id == self.env.user.id:
                self.env['tapis.security.incident'].create({
                    'name': _('Segregation of Duties: Self-approval on Budget %s') % rec.name,
                    'user_id': self.env.user.id,
                    'model_name': 'tapis.budget',
                    'operation': 'self_approve',
                    'description': _('User %s attempted to approve their own budget %s.') % (self.env.user.name, rec.name),
                    'severity': 'high',
                })
                raise UserError(_(
                    'Segregation of Duties Violation: You cannot approve a budget that you created. '
                    'This must be approved by another authorized user.'
                ))
        return super(Budget, self).action_confirm()

    def action_approve(self):
        for rec in self:
            if rec.create_uid.id == self.env.user.id:
                self.env['tapis.security.incident'].create({
                    'name': _('Segregation of Duties: Self-approval on Budget %s') % rec.name,
                    'user_id': self.env.user.id,
                    'model_name': 'tapis.budget',
                    'operation': 'self_approve',
                    'description': _('User %s attempted to approve their own budget %s.') % (self.env.user.name, rec.name),
                    'severity': 'high',
                })
                raise UserError(_(
                    'Segregation of Duties Violation: You cannot approve a budget that you created. '
                    'This must be approved by another authorized user.'
                ))
        return super(Budget, self).action_approve()


class ApprovalRequest(models.Model):
    _inherit = 'tapis.approval.request'

    def action_submit(self):
        for rec in self:
            if rec.create_uid.id == self.env.user.id:
                if any(line.approver_id.id == self.env.user.id for line in rec.line_ids):
                    self.env['tapis.security.incident'].create({
                        'name': _('Segregation of Duties: Self-approval on Approval %s') % rec.name,
                        'user_id': self.env.user.id,
                        'model_name': 'tapis.approval.request',
                        'operation': 'self_approve',
                        'description': _('User %s attempted to approve their own approval request %s.') % (self.env.user.name, rec.name),
                        'severity': 'high',
                    })
                    raise UserError(_(
                        'Segregation of Duties Violation: You cannot be both the requester and an approver '
                        'on the same approval request.'
                    ))
        return super(ApprovalRequest, self).action_submit()
