import json
import time
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TapisDesign(models.Model):
    _name = 'tapis.design'
    _description = 'Tapis Design'

    name = fields.Char(string='Design Name', required=True)
    designer_id = fields.Many2one(
        'tapis.employee',
        domain="[('role','=','designer')]"
    )
    image = fields.Binary(string='Design Image', attachment=True)
    image_filename = fields.Char(string='Image Filename')
    product_id = fields.Many2one('tapis.product', string='Related Product')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('in_production', 'In Production')
    ], string='Status', default='draft')
    document_count = fields.Integer(compute='_compute_document_count')

    length_cm = fields.Float(string='Length (cm)')
    width_cm = fields.Float(string='Width (cm)')
    area_m2 = fields.Float(string='Area (m²)', compute='_compute_geometry', store=True)

    density_kg_per_m2 = fields.Float(string='Density (kg/m²)', default=5.0)
    total_weight_kg = fields.Float(string='Total Weight (kg)', compute='_compute_geometry', store=True)

    color_line_ids = fields.One2many('tapis.design.color.line', 'design_id', string='Color Composition')
    ai_analysis_log_ids = fields.One2many('tapis.ai.analysis.log', 'design_id', string='AI Analysis Logs')
    notes = fields.Text(string='Notes')
    image_html = fields.Html(compute='_compute_image_html', sanitize=False)

    total_percentage = fields.Float(string='Total Percentage (%)', compute='_compute_validations', store=True)
    percentage_ok = fields.Boolean(string='Percentage OK', compute='_compute_validations', store=True)
    color_count = fields.Integer(string='Color Count', compute='_compute_validations', store=True)

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('design_id', '=', rec.id)])

    @api.depends('length_cm', 'width_cm', 'density_kg_per_m2')
    def _compute_geometry(self):
        for rec in self:
            if rec.length_cm and rec.width_cm:
                rec.area_m2 = (rec.length_cm * rec.width_cm) / 10000.0
                rec.total_weight_kg = rec.area_m2 * rec.density_kg_per_m2
            else:
                rec.area_m2 = 0.0
                rec.total_weight_kg = 0.0

    @api.depends('color_line_ids.percentage')
    def _compute_validations(self):
        for rec in self:
            lines = rec.color_line_ids
            rec.color_count = len(lines)
            if lines:
                rec.total_percentage = sum(lines.mapped('percentage'))
                rec.percentage_ok = abs(rec.total_percentage - 100.0) < 0.01
            else:
                rec.total_percentage = 0.0
                rec.percentage_ok = False

    def action_normalize_percentages(self):
        for rec in self:
            lines = rec.color_line_ids
            if not lines:
                raise UserError(_('No color lines to normalize.'))
            total = sum(lines.mapped('percentage'))
            if total == 0:
                raise UserError(_('Cannot normalize when all percentages are zero.'))
            for line in lines:
                line.percentage = (line.percentage / total) * 100.0

    def action_recalculate_weights(self):
        for rec in self:
            rec._compute_geometry()
            for line in rec.color_line_ids:
                line._compute_weight_kg()

    def action_clear_colors(self):
        for rec in self:
            rec.color_line_ids.unlink()

    def action_analyze_colors_ai(self):
        self.ensure_one()
        if not self.image:
            raise UserError(_('Please upload a design image before running AI analysis.'))

        provider = self.env['tapis.ai.provider'].search([('is_default', '=', True)], limit=1)
        if not provider:
            raise UserError(_(
                'No default AI provider configured. '
                'Go to Configuration > AI Providers and set one as default.'
            ))

        b64 = self.image.decode() if isinstance(self.image, bytes) else self.image

        prompt = (
            'Analyze this carpet design image.\n\n'
            'Tasks:\n'
            '1. Identify every visible color code label.\n'
            '2. Estimate the percentage of the rug occupied by each color.\n'
            '3. Return the colors in logical order using a sequence number.\n'
            '4. Ensure percentages sum to 100.\n'
            '5. Return ONLY valid JSON in the following format:\n\n'
            '[\n'
            '  {\n'
            '    "sequence": 1,\n'
            '    "color_code": "MT41",\n'
            '    "percentage": 70.0\n'
            '  }\n'
            ']\n\n'
            'Do not include explanations or markdown.'
        )

        request_time = fields.Datetime.now()
        t0 = time.time()
        error_msg = False
        raw_response_text = ''
        parsed_data = []

        try:
            raw_response_text = provider._send_request(prompt, b64)

            if raw_response_text:
                text = raw_response_text.strip()
                start = text.find('[')
                end = text.rfind(']') + 1
                if start >= 0 and end > start:
                    json_str = text[start:end]
                    parsed_data = json.loads(json_str)

        except Exception as e:
            error_msg = str(e)

        t1 = time.time()

        if error_msg or not parsed_data:
            self.env['tapis.ai.analysis.log'].create({
                'design_id': self.id,
                'provider_id': provider.id,
                'request_datetime': request_time,
                'response_datetime': fields.Datetime.now(),
                'duration_seconds': t1 - t0,
                'prompt_used': prompt,
                'raw_response': raw_response_text,
                'status': 'failed',
                'error_message': error_msg or _('No valid JSON data returned from AI.'),
            })
            raise UserError(_('AI Analysis failed: %s') % (error_msg or _('No valid JSON data returned.')))

        self.color_line_ids.unlink()
        for item in parsed_data:
            seq = item.get('sequence', 10)
            code = item.get('color_code', '')
            pct = item.get('percentage', 0.0)
            self.env['tapis.design.color.line'].create({
                'design_id': self.id,
                'sequence': seq,
                'color_code': code,
                'percentage': pct,
            })

        self.env['tapis.ai.analysis.log'].create({
            'design_id': self.id,
            'provider_id': provider.id,
            'request_datetime': request_time,
            'response_datetime': fields.Datetime.now(),
            'duration_seconds': t1 - t0,
            'prompt_used': prompt,
            'raw_response': raw_response_text,
            'parsed_json': json.dumps(parsed_data, indent=2),
            'status': 'success',
        })

        return

    @api.depends('image')
    def _compute_image_html(self):
        import base64
        for rec in self:
            if rec.image:
                b64 = rec.image.decode() if isinstance(rec.image, bytes) else rec.image
                raw = base64.b64decode(b64)
                if raw[:3] == b'\xff\xd8\xff':
                    mime = 'jpeg'
                elif raw[:4] == b'\x89PNG':
                    mime = 'png'
                elif raw[:4] == b'GIF8':
                    mime = 'gif'
                elif raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
                    mime = 'webp'
                elif raw[:2] == b'BM':
                    mime = 'bmp'
                else:
                    mime = 'png'
                rec.image_html = '<img src="data:image/%s;base64,%s" style="max-width:200px;max-height:200px;"/>' % (mime, b64)
            else:
                rec.image_html = False

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('design_id', '=', self.id)],
            'context': {'default_design_id': self.id},
            'target': 'current',
        }
