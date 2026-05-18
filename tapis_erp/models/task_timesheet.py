from odoo import _, models, fields, api


class TapisTaskTimesheet(models.Model):
    _name = 'tapis.task.timesheet'
    _description = 'Task Timesheet'
    _order = 'date desc, id desc'
    _rec_name = 'description'

    task_id = fields.Many2one('tapis.task', string='Task', required=True, ondelete='cascade')
    employee_id = fields.Many2one('tapis.employee', string='Employee', required=True)
    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    hours = fields.Float(string='Hours', required=True)
    description = fields.Char(string='Description')
