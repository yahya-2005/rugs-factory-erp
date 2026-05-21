import json
import base64
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WoolDesign(models.Model):
    _name = 'wool.design'
    _description = 'Wool Design'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, unique=True)
    description = fields.Text()
    image = fields.Binary(attachment=True)
    image_filename = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('analyzed', 'Analyzed'),
        ('approved', 'Approved'),
        ('archived', 'Archived'),
    ], default='draft', string='Status')

    length_cm = fields.Float(required=True)
    width_cm = fields.Float(required=True)
    surface_m2 = fields.Float(compute='_compute_dimensions', store=True)

    weight_factor = fields.Float(default=5.0)
    estimated_weight_kg = fields.Float(compute='_compute_dimensions', store=True)

    color_line_ids = fields.One2many('wool.design.color.line', 'design_id', string='Color Composition')
    notes = fields.Text()

    total_percentage = fields.Float(compute='_compute_validations', store=True)
    total_weight_allocated_kg = fields.Float(compute='_compute_validations', store=True)
    percentage_difference = fields.Float(compute='_compute_validations', store=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Design code must be unique!'),
    ]

    @api.depends('length_cm', 'width_cm', 'weight_factor')
    def _compute_dimensions(self):
        for rec in self:
            if rec.length_cm and rec.width_cm:
                rec.surface_m2 = (rec.length_cm * rec.width_cm) / 10000.0
                rec.estimated_weight_kg = rec.surface_m2 * rec.weight_factor
            else:
                rec.surface_m2 = 0.0
                rec.estimated_weight_kg = 0.0

    @api.depends('color_line_ids.percentage', 'color_line_ids.estimated_weight_kg', 'estimated_weight_kg')
    def _compute_validations(self):
        for rec in self:
            lines = rec.color_line_ids
            if lines:
                rec.total_percentage = sum(lines.mapped('percentage'))
                rec.total_weight_allocated_kg = sum(lines.mapped('estimated_weight_kg'))
                rec.percentage_difference = round(100.0 - rec.total_percentage, 2)
            else:
                rec.total_percentage = 0.0
                rec.total_weight_allocated_kg = 0.0
                rec.percentage_difference = 100.0

    def _detect_mime(self, image_data):
        raw = base64.b64decode(image_data)
        if raw[:3] == b'\xff\xd8\xff':
            return 'image/jpeg'
        elif raw[:4] == b'\x89PNG':
            return 'image/png'
        elif raw[:4] == b'GIF8':
            return 'image/gif'
        return 'image/jpeg'

    @api.depends('image')
    def _compute_image_html(self):
        for rec in self:
            if not rec.image or rec.image is True:
                rec.image_html = False
                continue
            try:
                b64 = rec.image.decode() if isinstance(rec.image, bytes) else rec.image
                raw = base64.b64decode(b64)
                if raw[:3] == b'\xff\xd8\xff':
                    mime = 'jpeg'
                elif raw[:4] == b'\x89PNG':
                    mime = 'png'
                elif raw[:4] == b'GIF8':
                    mime = 'gif'
                else:
                    mime = 'png'
                rec.image_html = '<img src="data:image/%s;base64,%s" style="max-width:200px;max-height:200px;"/>' % (mime, b64)
            except Exception:
                rec.image_html = False
    image_html = fields.Html(compute='_compute_image_html', sanitize=False)

    def action_analyze_with_ai(self):
        self.ensure_one()
        if not self.image:
            raise UserError(_('Please upload a design image first.'))
        if not self.color_line_ids:
            raise UserError(_('No color lines to analyze. Generate colors first.'))

        api_key = self.env['ir.config_parameter'].sudo().get_param('is_tapis_design.ai_api_key_gemini', '')
        if not api_key:
            raise UserError(_('Configure Gemini API key in System Parameters (is_tapis_design.ai_api_key_gemini).'))

        wool_colors = self.env['wool.color'].search([('active', '=', True)])
        color_list = '\n'.join([f"- {c.code}: {c.name} (hex: {c.color_hex or '#N/A'})" for c in wool_colors])

        prompt = (
            'You are analyzing a carpet/rug design image. '
            'Below is the reference color palette available:\n'
            f'{color_list}\n\n'
            'Identify which of these colors appear in the image and estimate '
            'their percentage coverage of the design surface.\n'
            'Return ONLY a JSON array with objects containing:\n'
            '- "color_code": the code of the matched color\n'
            '- "percentage": a float between 0 and 100\n\n'
            'Rules:\n'
            '- Only use color codes from the reference palette above\n'
            '- Percentages must sum to exactly 100\n'
            '- Include all colors that appear significantly (>5%)\n'
            '- Round percentages to 1 decimal place'
        )

        import requests
        b64_data = self.image.decode() if isinstance(self.image, bytes) else self.image
        mime = self._detect_mime(b64_data)

        model = 'gemini-flash-latest'
        url = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent' % model
        payload = {
            'contents': [{
                'parts': [
                    {'text': prompt},
                    {'inline_data': {'mime_type': mime, 'data': b64_data}},
                ]
            }]
        }

        resp = requests.post(url, json=payload, headers={'Content-Type': 'application/json', 'X-goog-api-key': api_key}, timeout=60)
        if resp.status_code != 200:
            err = resp.json().get('error', {}).get('message', resp.text[:200])
            raise UserError(_('Gemini API error: %s') % err)
        candidates = resp.json().get('candidates', [])
        if not candidates:
            raise UserError(_('No response from Gemini API.'))
        parts = candidates[0].get('content', {}).get('parts', [])
        response_text = ' '.join([p.get('text', '') for p in parts])

        text = response_text.strip()
        start = text.find('[')
        end = text.rfind(']') + 1
        if start < 0 or end <= start:
            raise UserError(_('Could not parse AI response. Response: %s') % text[:200])

        data = json.loads(text[start:end])

        color_map = {c.code: c.id for c in wool_colors}
        for item in data:
            code = item.get('color_code', '')
            pct = item.get('percentage', 0.0)
            if code in color_map:
                line = self.color_line_ids.filtered(lambda l, c=code: l.wool_color_id.code == c)
                if line:
                    line.write({'percentage': pct})

        self.state = 'analyzed'

    def action_generate_color_lines(self):
        self.ensure_one()
        if self.color_line_ids:
            raise UserError(_('Color lines already exist. Clear them first.'))
        WoolColor = self.env['wool.color']
        colors = WoolColor.search([('active', '=', True)], limit=5)
        for i, color in enumerate(colors):
            self.env['wool.design.color.line'].create({
                'design_id': self.id,
                'sequence': (i + 1) * 10,
                'wool_color_id': color.id,
                'percentage': 20.0,
            })

    def action_validate_percentages(self):
        self.ensure_one()
        if abs(self.total_percentage - 100.0) > 0.01:
            raise UserError(_(
                'Total percentage must equal 100%%. Current total: %.2f%% (difference: %.2f%%)') % (
                self.total_percentage, self.percentage_difference))
        if not self.color_line_ids:
            raise UserError(_('Add at least one color line.'))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Percentages Valid'),
                'message': _('Total composition: %.2f%%') % self.total_percentage,
                'sticky': False,
                'type': 'success',
            },
        }

    def action_approve(self):
        self.ensure_one()
        if abs(self.total_percentage - 100.0) > 0.01:
            raise UserError(_(
                'Cannot approve. Total percentage must be 100%%. Current: %.2f%%') % self.total_percentage)
        self.state = 'approved'
        template = self.env.ref('is_tapis_design.email_template_design_approved', False)
        if template:
            template.send_mail(self.id, force_send=True)

    def action_reset_draft(self):
        self.state = 'draft'

    def action_archive(self):
        self.state = 'archived'
