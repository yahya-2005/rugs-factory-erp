import requests
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AiProvider(models.Model):
    _name = 'tapis.ai.provider'
    _description = 'AI Provider'
    _order = 'name'

    name = fields.Char(required=True)
    provider_type = fields.Selection([
        ('openai', 'OpenAI'),
        ('gemini', 'Google Gemini'),
        ('ollama', 'Ollama'),
    ], required=True, default='ollama')
    api_key = fields.Char(string='API Key')
    base_url = fields.Char(string='Base URL')
    model_name = fields.Char(string='Model Name')
    timeout_seconds = fields.Integer(string='Timeout (seconds)', default=120)
    active = fields.Boolean(default=True)
    is_default = fields.Boolean(default=False)

    @api.constrains('is_default')
    def _check_default(self):
        for rec in self:
            if rec.is_default:
                others = self.search([('is_default', '=', True), ('id', '!=', rec.id)])
                if others:
                    others.write({'is_default': False})

    def action_test_connection(self):
        self.ensure_one()
        prompt = 'Respond with ONLY the word "OK" and nothing else.'
        try:
            response_text = self._send_request(prompt, None)
            if response_text and 'OK' in response_text.strip().upper():
                raise UserError(_('Connection successful! Provider responded correctly.'))
            else:
                raise UserError(_('Connection successful but unexpected response: %s') % response_text[:200])
        except Exception as e:
            raise UserError(_('Connection failed: %s') % str(e))

    def _send_request(self, prompt, image_b64):
        self.ensure_one()
        headers = {}
        timeout = self.timeout_seconds or 120

        if self.provider_type == 'ollama':
            url = (self.base_url or 'http://localhost:11434').rstrip('/') + '/api/generate'
            payload = {
                'model': self.model_name or 'llama3.2-vision',
                'prompt': prompt,
                'stream': False,
            }
            if image_b64:
                payload['images'] = [image_b64]
            if self.api_key:
                headers['Authorization'] = 'Bearer ' + self.api_key
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            result = resp.json()
            return result.get('response', '')

        elif self.provider_type == 'openai':
            url = (self.base_url or 'https://api.openai.com/v1').rstrip('/') + '/chat/completions'
            content = [{'type': 'text', 'text': prompt}]
            if image_b64:
                content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + image_b64}})
            payload = {
                'model': self.model_name or 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': content}],
            }
            headers['Content-Type'] = 'application/json'
            if self.api_key:
                headers['Authorization'] = 'Bearer ' + self.api_key
            if self.base_url and 'openrouter' in self.base_url.lower():
                headers['HTTP-Referer'] = 'https://tapis-erp.local'
                headers['X-Title'] = 'Tapis ERP'
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if not resp.ok:
                raise UserError(_('API error %s: %s') % (resp.status_code, resp.text[:500]))
            resp.raise_for_status()
            result = resp.json()
            return result.get('choices', [{}])[0].get('message', {}).get('content', '')

        elif self.provider_type == 'gemini':
            model = self.model_name or 'gemini-1.5-flash'
            api_key = self.api_key or ''
            if not api_key:
                raise UserError(_('API Key is required for Google Gemini.'))
            url = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (model, api_key)
            parts = [{'text': prompt}]
            if image_b64:
                parts.append({'inline_data': {'mime_type': 'image/png', 'data': image_b64}})
            payload = {'contents': [{'parts': parts}]}
            headers['Content-Type'] = 'application/json'
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            result = resp.json()
            candidates = result.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                return ' '.join([p.get('text', '') for p in parts])
            return ''

        raise UserError(_('Unknown provider type: %s') % self.provider_type)
