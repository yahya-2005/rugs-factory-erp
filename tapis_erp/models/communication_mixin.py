from odoo import _, models, fields, api
from odoo.exceptions import UserError
import json
from datetime import datetime


class TapisCommunicationMixin(models.AbstractModel):
    _name = 'tapis.communication.mixin'
    _description = 'Communication Mixin'

    def _trigger_communication(self, event_code):
        self.ensure_one()
        templates = self.env['tapis.communication.template'].search([
            ('code', '=', event_code),
            ('active', '=', True),
        ])
        for tmpl in templates:
            if tmpl.model_name and tmpl.model_name != self._name:
                continue
            if tmpl.condition_domain:
                try:
                    domain = json.loads(tmpl.condition_domain)
                    if not self.filtered_domain(domain):
                        self._log_communication(tmpl, status='skipped', error=_('Condition domain not met'))
                        continue
                except Exception:
                    pass
            recipients = self._get_notification_recipients(tmpl)
            if not recipients:
                self._log_communication(tmpl, status='skipped', error=_('No recipients found'))
                continue
            emails = list(set(recipients))
            subject = self._render_template(tmpl.email_subject, tmpl)
            body = self._render_template(tmpl.email_body, tmpl)
            mail_message = False
            error_msg = False
            if tmpl.send_email:
                try:
                    mail_message = self._send_notification_email(emails, subject, body)
                except Exception as e:
                    error_msg = str(e)
            if tmpl.create_activity:
                try:
                    self._create_activities(tmpl)
                except Exception as e:
                    error_msg = (error_msg or '') + ('; Activity: ' + str(e) if error_msg else 'Activity: ' + str(e))
            status = 'failed' if error_msg and not mail_message else 'sent' if mail_message else 'pending'
            self._log_communication(tmpl, status=status, error=error_msg, emails=emails,
                                    subject=subject, mail_message_id=mail_message)

    def _get_notification_recipients(self, template):
        self.ensure_one()
        if template.recipient_type == 'specific_users':
            return [u.email or u.login for u in template.user_ids if u.email or u.login]
        elif template.recipient_type == 'record_owner':
            user = self.env.user
            if user.email:
                return [user.email]
            return []
        elif template.recipient_type == 'manager':
            group = self.env.ref('tapis_erp.group_tapis_manager', raise_if_not_found=False)
            if group:
                return list(set(u.email or u.login for u in group.users if u.email or u.login))
            return []
        elif template.recipient_type == 'customer':
            email = self._get_customer_email()
            return [email] if email else []
        elif template.recipient_type == 'supplier':
            email = self._get_supplier_email()
            return [email] if email else []
        return []

    def _get_customer_email(self):
        return False

    def _get_supplier_email(self):
        return False

    def _render_template(self, content, template):
        self.ensure_one()
        result = content
        placeholders = self._get_placeholders()
        for key, val in placeholders.items():
            result = result.replace('{{%s}}' % key, str(val or ''))
        return result

    def _get_placeholders(self):
        self.ensure_one()
        vals = {'id': self.id, 'name': str(getattr(self, 'name', '') or ''),
                'display_name': str(self.display_name or ''), 'user': self.env.user.name,
                'date': fields.Date.today().strftime('%Y-%m-%d'),
                'datetime': fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}
        for fname in ('state', 'code', 'email', 'phone', 'amount_total', 'total_price',
                       'expected_revenue', 'deadline', 'scheduled_date', 'stock_qty'):
            if fname in self._fields:
                val = getattr(self, fname, '')
                vals[fname] = str(val if val else '')
        return vals

    def _send_notification_email(self, recipient_emails, subject, body):
        for email in recipient_emails:
            if email:
                self.message_post(
                    subject=subject,
                    body=body,
                    partner_ids=[],
                    email_from=self.env.user.email or self.env.company.email or False,
                    message_type='email',
                    subtype_xmlid='mail.mt_comment',
                )
        return self.env['mail.message'].search([('model', '=', self._name),
                                                 ('res_id', '=', self.id),
                                                 ('subject', '=', subject)],
                                                order='id desc', limit=1)

    def _create_activities(self, template):
        self.ensure_one()
        if not template.activity_type_id:
            return
        for user in self._get_activity_users(template):
            self.activity_schedule(
                template.activity_type_id.id,
                summary=_(template.email_subject),
                note=_(template.email_body),
                user_id=user.id,
            )

    def _get_activity_users(self, template):
        if template.recipient_type == 'specific_users':
            return template.user_ids
        elif template.recipient_type == 'record_owner':
            return self.env.user
        elif template.recipient_type == 'manager':
            group = self.env.ref('tapis_erp.group_tapis_manager', raise_if_not_found=False)
            return group.users if group else self.env['res.users']
        return self.env['res.users']

    def _log_communication(self, template, status='pending', error=None, emails=None,
                            subject=None, mail_message_id=None):
        self.ensure_one()
        self.env['tapis.communication.log'].create({
            'name': '%s - %s' % (template.code, self.display_name or str(self.id)),
            'template_id': template.id,
            'model_name': self._name,
            'record_id': self.id,
            'recipient_emails': '\n'.join(emails) if emails else False,
            'subject': subject or template.email_subject,
            'status': status,
            'sent_date': fields.Datetime.now() if status == 'sent' else False,
            'error_message': error,
            'mail_message_id': mail_message_id.id if mail_message_id else False,
            'user_id': self.env.user.id,
        })

    @api.model
    def _cron_check_overdue_invoices(self):
        today = fields.Date.today()
        invoices = self.env['tapis.invoice'].search([
            ('state', '=', 'posted'),
            ('payment_status', 'in', ('unpaid', 'partial')),
            ('due_date', '<', today),
        ])
        for inv in invoices:
            inv._trigger_communication('INVOICE_OVERDUE')

    @api.model
    def _cron_check_low_stock(self):
        products = self.env['tapis.product'].search([('stock_qty', '<', 5)])
        for prod in products:
            prod._trigger_communication('LOW_STOCK_ALERT')

    @api.model
    def _cron_check_document_expiration(self):
        today = fields.Date.today()
        documents = self.env['tapis.document'].search([
            ('expiration_date', '!=', False),
            ('expiration_date', '<=', today),
            ('state', '=', 'approved'),
        ])
        for doc in documents:
            doc._trigger_communication('DOCUMENT_EXPIRING')

    @api.model
    def _cron_check_task_deadlines(self):
        today = fields.Date.today()
        tasks = self.env['tapis.task'].search([
            ('deadline', '!=', False),
            ('deadline', '<=', today),
            ('state', 'not in', ('done', 'cancelled')),
        ])
        for task in tasks:
            task._trigger_communication('TASK_DEADLINE')

    @api.model
    def _cron_check_maintenance_due(self):
        today = fields.Datetime.now()
        orders = self.env['tapis.maintenance.order'].search([
            ('state', '=', 'scheduled'),
            ('scheduled_date', '<=', today),
        ])
        for order in orders:
            order._trigger_communication('MAINTENANCE_DUE')

    @api.model
    def _cron_check_budget_overruns(self):
        budgets = self.env['tapis.budget'].search([('state', '=', 'approved')])
        for budget in budgets:
            if budget.total_variance < 0:
                budget._trigger_communication('BUDGET_OVER_LIMIT')
