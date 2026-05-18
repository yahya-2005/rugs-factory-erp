from odoo import models, fields, api


class TapisDocumentFolder(models.Model):
    _name = 'tapis.document.folder'
    _description = 'Document Folder'
    _rec_name = 'complete_name'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True)
    parent_id = fields.Many2one('tapis.document.folder', string='Parent Folder')
    child_ids = fields.One2many('tapis.document.folder', 'parent_id', string='Sub-Folders')
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color', default=0)
    description = fields.Text(string='Description')
    document_count = fields.Integer(string='Document Count', compute='_compute_document_count', store=True)
    complete_name = fields.Char(string='Full Path', compute='_compute_complete_name', store=True)
    active = fields.Boolean(string='Active', default=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = '%s / %s' % (rec.parent_id.complete_name, rec.name)
            else:
                rec.complete_name = rec.name

    @api.depends('child_ids.document_count')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('folder_id', '=', rec.id)])
