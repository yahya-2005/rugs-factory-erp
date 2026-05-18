from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisQualityInspection(models.Model):
    _name = 'tapis.quality.inspection'
    _description = 'Quality Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'inspection_date desc, id desc'

    name = fields.Char(
        string='Inspection Reference',
        required=True,
        tracking=True
    )

    production_id = fields.Many2one(
        'tapis.production',
        string='Production Order',
        required=True,
        tracking=True
    )

    product_id = fields.Many2one(
        'tapis.product',
        string='Product',
        related='production_id.product_id',
        store=True,
        readonly=True
    )

    inspector_id = fields.Many2one(
        'tapis.employee',
        string='Inspector',
        tracking=True
    )

    inspection_date = fields.Date(
        string='Inspection Date',
        default=fields.Date.today,
        tracking=True
    )

    appearance_score = fields.Float(
        string='Appearance Score',
        help='Score for visual appearance (0-100)'
    )

    dimensions_score = fields.Float(
        string='Dimensions Score',
        help='Score for dimensional accuracy (0-100)'
    )

    weaving_score = fields.Float(
        string='Weaving Score',
        help='Score for weaving quality (0-100)'
    )

    finishing_score = fields.Float(
        string='Finishing Score',
        help='Score for edge finishing quality (0-100)'
    )

    average_score = fields.Float(
        string='Average Score',
        compute='_compute_average_score',
        store=True
    )

    result = fields.Selection([
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ], string='Result', default='pending', tracking=True)

    defect_notes = fields.Text(string='Defect Notes')

    corrective_action = fields.Text(string='Corrective Action')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True)
    document_count = fields.Integer(compute='_compute_document_count')

    @api.depends('appearance_score', 'dimensions_score', 'weaving_score', 'finishing_score')
    def _compute_average_score(self):
        for rec in self:
            scores = [s for s in [
                rec.appearance_score,
                rec.dimensions_score,
                rec.weaving_score,
                rec.finishing_score
            ] if s]
            rec.average_score = sum(scores) / len(scores) if scores else 0.0

    def action_set_passed(self):
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError(_('Cannot set result on a cancelled inspection.'))
            rec.result = 'passed'

    def action_set_failed(self):
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError(_('Cannot set result on a cancelled inspection.'))
            rec.result = 'failed'

    def action_complete(self):
        for rec in self:
            if rec.result == 'pending':
                raise UserError(_('Please set a result (Passed or Failed) before completing the inspection.'))
            rec.state = 'completed'
            rec.message_post(
                body=_('Quality inspection %s completed with result: %s')
                      % (rec.name, dict(rec._fields['result'].selection).get(rec.result))
            )

    def action_cancel(self):
        for rec in self:
            if rec.state == 'completed':
                raise UserError(_('Cannot cancel a completed inspection.'))
            rec.state = 'cancelled'
            rec.message_post(
                body=_('Quality inspection %s cancelled.') % rec.name
            )

    def action_open_production(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Production Order',
            'res_model': 'tapis.production',
            'view_mode': 'form',
            'res_id': self.production_id.id,
            'target': 'current',
        }

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('quality_inspection_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('quality_inspection_id', '=', self.id)],
            'context': {'default_quality_inspection_id': self.id},
            'target': 'current',
        }
