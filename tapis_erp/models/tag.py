from odoo import models, fields


class TapisTag(models.Model):
    _name = 'tapis.tag'
    _description = 'Tapis Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color')
