from odoo import _, models, fields, api
from odoo.exceptions import UserError
import base64


class TapisDocument(models.Model):
    _name = 'tapis.document'
    _description = 'Document'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.approval.mixin', 'tapis.communication.mixin', 'tapis.audit.mixin', 'tapis.signature.mixin']
    _rec_name = 'name'
    _order = 'upload_date desc, id desc'

    name = fields.Char(string='Document Name', required=True, tracking=True)
    code = fields.Char(string='Document Code', readonly=True, default=lambda s: _('New'), tracking=True)
    folder_id = fields.Many2one('tapis.document.folder', string='Folder', required=True, tracking=True)

    attachment = fields.Binary(string='File', attachment=True, required=True)
    attachment_filename = fields.Char(string='Filename')

    file_type = fields.Selection([
        ('pdf', 'PDF'),
        ('image', 'Image'),
        ('excel', 'Excel'),
        ('word', 'Word'),
        ('zip', 'Archive (ZIP)'),
        ('other', 'Other'),
    ], string='File Type', compute='_compute_file_type', store=True)
    file_size_kb = fields.Float(string='File Size (KB)', compute='_compute_file_size', store=True)
    version = fields.Char(string='Version', default='1.0', tracking=True)
    description = fields.Html(string='Description')
    tag_ids = fields.Many2many('tapis.project.tag', string='Tags')
    uploaded_by_id = fields.Many2one('res.users', string='Uploaded By', default=lambda s: s.env.user)
    upload_date = fields.Datetime(string='Upload Date', default=fields.Datetime.now, tracking=True)
    expiration_date = fields.Date(string='Expiration Date')
    is_expired = fields.Boolean(string='Expired', compute='_compute_is_expired', store=True)

    product_id = fields.Many2one('tapis.product', string='Product', tracking=True)
    customer_id = fields.Many2one('tapis.customer', string='Customer', tracking=True)
    supplier_id = fields.Many2one('tapis.supplier', string='Supplier', tracking=True)
    purchase_id = fields.Many2one('tapis.purchase', string='Purchase Order', tracking=True)
    sale_id = fields.Many2one('tapis.sale', string='Sale Order', tracking=True)
    design_id = fields.Many2one('tapis.design', string='Design', tracking=True)
    production_id = fields.Many2one('tapis.production', string='Production Order', tracking=True)
    invoice_id = fields.Many2one('tapis.invoice', string='Invoice', tracking=True)
    quality_inspection_id = fields.Many2one('tapis.quality.inspection', string='Quality Inspection', tracking=True)
    equipment_id = fields.Many2one('tapis.equipment', string='Equipment', tracking=True)
    maintenance_id = fields.Many2one('tapis.maintenance.order', string='Maintenance Order', tracking=True)
    employee_id = fields.Many2one('tapis.employee', string='Employee', tracking=True)
    project_id = fields.Many2one('tapis.project', string='Project', tracking=True)
    task_id = fields.Many2one('tapis.task', string='Task', tracking=True)
    budget_id = fields.Many2one('tapis.budget', string='Budget', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', required=True, tracking=True)
    approval_count = fields.Integer(compute='_compute_approval_count')

    @api.depends('attachment_filename')
    def _compute_file_type(self):
        for rec in self:
            fname = (rec.attachment_filename or '').lower()
            if fname.endswith('.pdf'):
                rec.file_type = 'pdf'
            elif any(fname.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp')):
                rec.file_type = 'image'
            elif any(fname.endswith(ext) for ext in ('.xls', '.xlsx', '.csv')):
                rec.file_type = 'excel'
            elif any(fname.endswith(ext) for ext in ('.doc', '.docx')):
                rec.file_type = 'word'
            elif any(fname.endswith(ext) for ext in ('.zip', '.rar', '.7z', '.tar', '.gz')):
                rec.file_type = 'zip'
            else:
                rec.file_type = 'other'

    @api.depends('attachment')
    def _compute_file_size(self):
        for rec in self:
            if rec.attachment:
                rec.file_size_kb = round(len(base64.b64decode(rec.attachment)) / 1024.0, 2)
            else:
                rec.file_size_kb = 0.0

    @api.depends('expiration_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_expired = bool(rec.expiration_date and rec.expiration_date < today)

    def action_approve(self):
        for rec in self:
            if rec.state == 'archived':
                raise UserError(_('Archived documents cannot be approved.'))
            rec.state = 'approved'
            rec.message_post(body=_('Document approved.'))

    def action_archive(self):
        for rec in self:
            if rec.state == 'archived':
                continue
            rec.state = 'archived'
            rec.message_post(body=_('Document archived.'))

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'draft':
                continue
            rec.state = 'draft'
            rec.message_post(body=_('Document reset to draft.'))

    def _compute_approval_count(self):
        for rec in self:
            rec.approval_count = self.env['tapis.approval.request'].search_count([
                ('reference_model', '=', 'tapis.document'), ('reference_id', '=', rec.id)])

    def _get_approval_amount(self):
        return 0.0

    def _get_approval_category_code(self):
        return 'document'

    def action_download(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/%s' % (self._name, self.id, self.attachment_filename or 'file'),
            'target': 'self',
        }

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('tapis.document.code') or _('New')
        return super().create(vals)
