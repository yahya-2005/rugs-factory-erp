from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MultiCompanyMixin(models.AbstractModel):
    _name = 'tapis.multicompany.mixin'
    _description = 'Multi-Company Mixin'

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    is_shared = fields.Boolean(
        string='Shared Across Companies',
        default=False,
        help='If enabled, this record is visible to all companies.'
    )
