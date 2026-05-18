from odoo import _, api, fields, models


class TapisSignatureTemplate(models.Model):
    _name = 'tapis.signature.template'
    _description = 'Signature Template'
    _order = 'name asc'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    model_name = fields.Char(required=True)
    description = fields.Text()

    require_all_signers = fields.Boolean(default=True)
    allow_reject = fields.Boolean(default=True)
    auto_complete_record = fields.Boolean(default=False)

    signer_role_ids = fields.One2many('tapis.signature.role', 'template_id', string='Signer Roles')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Template code must be unique!'),
    ]


class TapisSignatureRole(models.Model):
    _name = 'tapis.signature.role'
    _description = 'Signature Role'
    _order = 'sequence, id'

    template_id = fields.Many2one('tapis.signature.template', string='Template', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    required = fields.Boolean(default=True)
    user_ids = fields.Many2many('res.users', string='Users')
    can_reject = fields.Boolean(default=True)
