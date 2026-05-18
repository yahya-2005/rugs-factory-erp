from odoo import _, models, fields, api


class TapisSupportTicket(models.Model):
    _name = 'tapis.support.ticket'
    _description = 'Support Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(required=True, readonly=True, default='New')
    customer_id = fields.Many2one('tapis.customer', string='Customer', required=True, tracking=True)
    contact_name = fields.Char(string='Contact Name')
    contact_email = fields.Char(string='Contact Email')
    subject = fields.Char(required=True, tracking=True)
    description = fields.Html(string='Description')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], default='medium', tracking=True)
    category = fields.Selection([
        ('sales', 'Sales'),
        ('production', 'Production'),
        ('invoice', 'Invoice'),
        ('delivery', 'Delivery'),
        ('technical', 'Technical'),
    ], default='sales', tracking=True)
    state = fields.Selection([
        ('new', 'New'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('waiting_customer', 'Waiting Customer'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], default='new', tracking=True)
    assigned_user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)
    resolution_notes = fields.Html(string='Resolution Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('tapis.support.ticket') or 'New'
        return super().create(vals_list)

    def action_assign(self):
        self.assigned_user_id = self.env.user
        self.state = 'assigned'
        self.message_post(body=_('Ticket assigned to %s.') % self.env.user.name)

    def action_start(self):
        self.state = 'in_progress'
        self.message_post(body=_('Ticket is now in progress.'))

    def action_wait_customer(self):
        self.state = 'waiting_customer'
        self.message_post(body=_('Waiting for customer response.'))

    def action_resolve(self):
        self.state = 'resolved'
        self.message_post(body=_('Ticket resolved.'))

    def action_close(self):
        self.state = 'closed'
        self.message_post(body=_('Ticket closed.'))

    def action_reopen(self):
        self.state = 'in_progress'
        self.message_post(body=_('Ticket reopened.'))
