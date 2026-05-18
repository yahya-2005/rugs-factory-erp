from odoo import _, models, fields, api
import secrets


class TapisPortalAccessToken(models.Model):
    _name = 'tapis.portal.access.token'
    _description = 'Portal Access Token'
    _rec_name = 'customer_id'

    customer_id = fields.Many2one('tapis.customer', string='Customer', required=True)
    token = fields.Char(required=True, unique=True, readonly=True, default=lambda self: secrets.token_urlsafe(32))
    expiration_date = fields.Datetime(string='Expiration Date')
    active = fields.Boolean(default=True)
    last_access_datetime = fields.Datetime(string='Last Access', readonly=True)

    def action_generate(self):
        for rec in self:
            rec.token = secrets.token_urlsafe(32)

    @api.model
    def generate_for_customer(self, customer):
        return self.create({
            'customer_id': customer.id,
        })

    def is_valid(self):
        self.ensure_one()
        if not self.active:
            return False
        if self.expiration_date and self.expiration_date < fields.Datetime.now():
            return False
        return True

    def update_access(self):
        self.last_access_datetime = fields.Datetime.now()
