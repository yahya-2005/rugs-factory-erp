from odoo import models, fields, api


class TapisAnalyticsDashboardCRM(models.Model):
    _inherit = 'tapis.analytics.dashboard'

    total_open_leads = fields.Integer(compute='_compute_analytics_crm')
    total_weighted_pipeline = fields.Float(compute='_compute_analytics_crm')
    crm_win_rate = fields.Float(compute='_compute_analytics_crm')
    leads_closing_this_month = fields.Integer(compute='_compute_analytics_crm')

    def action_view_crm_pipeline(self):
        return self._open_action('tapis.crm.lead', 'CRM Pipeline', 'kanban,tree,form')

    def action_view_closing_this_month(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1)
        return self._open_action('tapis.crm.lead', 'Closing This Month', 'kanban,tree,form',
            domain=[('expected_closing_date', '>=', month_start.strftime('%Y-%m-%d')),
                    ('expected_closing_date', '<', month_end.strftime('%Y-%m-%d')),
                    ('state', '=', 'open')])

    def _compute_analytics_crm(self):
        for rec in self:
            leads = self.env['tapis.crm.lead'].search([])
            open_leads = leads.filtered(lambda l: l.state == 'open')
            won_leads = leads.filtered(lambda l: l.state == 'won')
            lost_leads = leads.filtered(lambda l: l.state == 'lost')
            rec.total_open_leads = len(open_leads)
            rec.total_weighted_pipeline = sum(open_leads.mapped('weighted_revenue'))
            total_closed = len(won_leads) + len(lost_leads)
            rec.crm_win_rate = (len(won_leads) / total_closed * 100) if total_closed else 0.0
            today = fields.Date.today()
            month_start = today.replace(day=1)
            if today.month == 12:
                month_end = today.replace(year=today.year + 1, month=1, day=1)
            else:
                month_end = today.replace(month=today.month + 1, day=1)
            rec.leads_closing_this_month = len(open_leads.filtered(
                lambda l: l.expected_closing_date and month_start <= l.expected_closing_date < month_end
            ))
