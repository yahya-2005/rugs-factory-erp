from odoo import models, fields, api


class TapisDashboard(models.Model):
    _name = 'tapis.dashboard'
    _description = 'Tapis Dashboard'

    name = fields.Char(default="Dashboard")

    total_products = fields.Integer(compute='_compute_dashboard')
    total_designs = fields.Integer(compute='_compute_dashboard')
    total_wool_required = fields.Float(compute='_compute_dashboard')
    average_design_weight = fields.Float(compute='_compute_dashboard')
    designs_with_invalid_percentages = fields.Integer(compute='_compute_dashboard')
    total_productions = fields.Integer(compute='_compute_dashboard')
    total_sales = fields.Integer(compute='_compute_dashboard')
    total_purchases = fields.Integer(compute='_compute_dashboard')
    total_suppliers = fields.Integer(compute='_compute_dashboard')
    total_employees = fields.Integer(compute='_compute_dashboard')
    total_stock = fields.Integer(compute='_compute_dashboard')
    inventory_value = fields.Float(compute='_compute_dashboard')
    total_sales_revenue = fields.Float(compute='_compute_dashboard')
    total_purchase_cost = fields.Float(compute='_compute_dashboard')
    low_stock_count = fields.Integer(compute='_compute_dashboard')
    total_revenue = fields.Float(compute='_compute_dashboard')
    products_to_reorder = fields.Integer(compute='_compute_dashboard')
    total_recommended_purchase_qty = fields.Float(compute='_compute_dashboard')
    total_profit = fields.Float(compute='_compute_dashboard')
    average_margin_percent = fields.Float(compute='_compute_dashboard')
    total_customer_receivables = fields.Float(compute='_compute_dashboard')
    raw_material_count = fields.Integer(compute='_compute_dashboard')
    raw_material_inventory_value = fields.Float(compute='_compute_dashboard')
    low_raw_material_count = fields.Integer(compute='_compute_dashboard')
    avg_manufacturing_cost = fields.Float(compute='_compute_dashboard')
    total_quality_inspections = fields.Integer(compute='_compute_dashboard')
    passed_inspections = fields.Integer(compute='_compute_dashboard')
    failed_inspections = fields.Integer(compute='_compute_dashboard')
    quality_pass_rate = fields.Float(compute='_compute_dashboard')
    total_invoices = fields.Integer(compute='_compute_dashboard')
    unpaid_invoices = fields.Integer(compute='_compute_dashboard')
    total_invoice_amount = fields.Float(compute='_compute_dashboard')
    total_receivables_from_invoices = fields.Float(compute='_compute_dashboard')

    total_equipment = fields.Integer(compute='_compute_dashboard')
    broken_equipment_count = fields.Integer(compute='_compute_dashboard')
    under_maintenance_equipment_count = fields.Integer(compute='_compute_dashboard')
    total_equipment_maintenance_cost = fields.Float(compute='_compute_dashboard')
    overdue_maintenance_count = fields.Integer(compute='_compute_dashboard')
    total_equipment_downtime = fields.Float(compute='_compute_dashboard')
    total_projects = fields.Integer(compute='_compute_dashboard')
    active_projects = fields.Integer(compute='_compute_dashboard')
    total_tasks = fields.Integer(compute='_compute_dashboard')
    overdue_tasks = fields.Integer(compute='_compute_dashboard')
    tasks_in_review = fields.Integer(compute='_compute_dashboard')
    total_timesheet_hours = fields.Float(compute='_compute_dashboard')
    total_open_leads = fields.Integer(compute='_compute_dashboard')
    total_weighted_pipeline = fields.Float(compute='_compute_dashboard')
    crm_win_rate = fields.Float(compute='_compute_dashboard')
    leads_closing_this_month = fields.Integer(compute='_compute_dashboard')

    total_pending_approval_purchases = fields.Integer(compute='_compute_dashboard')
    avg_delivery_delay = fields.Float(compute='_compute_dashboard')
    on_time_delivery_rate = fields.Float(compute='_compute_dashboard')

    pending_approvals = fields.Integer(compute='_compute_dashboard')
    approvals_approved_today = fields.Integer(compute='_compute_dashboard')
    approvals_rejected_today = fields.Integer(compute='_compute_dashboard')
    average_approval_time = fields.Float(compute='_compute_dashboard')

    emails_sent_today = fields.Integer(compute='_compute_dashboard')
    failed_emails = fields.Integer(compute='_compute_dashboard')
    pending_notifications = fields.Integer(compute='_compute_dashboard')
    overdue_alerts = fields.Integer(compute='_compute_dashboard')

    total_automation_jobs = fields.Integer(compute='_compute_dashboard')
    active_jobs = fields.Integer(compute='_compute_dashboard')
    failed_jobs_today = fields.Integer(compute='_compute_dashboard')
    automation_success_rate = fields.Float(compute='_compute_dashboard')
    average_job_duration = fields.Float(compute='_compute_dashboard')
    pending_next_runs = fields.Integer(compute='_compute_dashboard')

    total_documents = fields.Integer(compute='_compute_dashboard')
    expired_documents = fields.Integer(compute='_compute_dashboard')
    documents_pending_approval = fields.Integer(compute='_compute_dashboard')

    total_changes_today = fields.Integer(compute='_compute_dashboard')
    most_modified_model = fields.Char(compute='_compute_dashboard')
    active_users_today = fields.Integer(compute='_compute_dashboard')
    deletion_count = fields.Integer(compute='_compute_dashboard')

    pending_signatures = fields.Integer(compute='_compute_dashboard')
    signed_today = fields.Integer(compute='_compute_dashboard')
    rejected_signatures = fields.Integer(compute='_compute_dashboard')

    active_companies = fields.Integer(compute='_compute_dashboard')
    consolidated_revenue = fields.Float(compute='_compute_dashboard')
    consolidated_profit = fields.Float(compute='_compute_dashboard')
    intercompany_transactions_count = fields.Integer(compute='_compute_dashboard')

    security_incidents_today = fields.Integer(compute='_compute_dashboard')
    blocked_access_attempts = fields.Integer(compute='_compute_dashboard')
    high_severity_incidents = fields.Integer(compute='_compute_dashboard')
    users_with_global_access = fields.Integer(compute='_compute_dashboard')

    def _compute_dashboard(self):
        for rec in self:
            products = self.env['tapis.product'].search([])
            sales = self.env['tapis.sale'].search([])
            purchases = self.env['tapis.purchase'].search([])

            rec.total_products = self.env['tapis.product'].search_count([])
            designs = self.env['tapis.design'].search([])
            rec.total_designs = len(designs)
            rec.total_wool_required = sum(designs.mapped('total_weight_kg'))
            weights = designs.mapped('total_weight_kg')
            rec.average_design_weight = sum(weights) / len(weights) if weights else 0.0
            rec.designs_with_invalid_percentages = len(designs.filtered(
                lambda d: d.color_count > 0 and not d.percentage_ok
            ))
            rec.total_productions = self.env['tapis.production'].search_count([])
            rec.total_sales = self.env['tapis.sale'].search_count([])
            rec.total_purchases = self.env['tapis.purchase'].search_count([])
            rec.total_suppliers = self.env['tapis.supplier'].search_count([])
            rec.total_employees = self.env['tapis.employee'].search_count([])

            rec.total_stock = sum(products.mapped('stock_qty'))
            rec.inventory_value = sum(p.stock_qty * p.cost for p in products)
            rec.low_stock_count = len(products.filtered(lambda p: p.stock_qty < 5))

            delivered_sales = sales.filtered(lambda s: s.state == 'delivered')
            rec.total_sales_revenue = sum(delivered_sales.mapped('total_price'))
            rec.total_revenue = rec.total_sales_revenue

            received_purchases = purchases.filtered(lambda p: p.state == 'received')
            rec.total_purchase_cost = sum(received_purchases.mapped('total_price'))

            rec.total_pending_approval_purchases = len(purchases.filtered(lambda p: p.state == 'pending_approval'))
            delays = received_purchases.mapped('delivery_delay_days')
            rec.avg_delivery_delay = sum(delays) / len(delays) if delays else 0.0
            on_time = len(received_purchases.filtered(lambda p: p.delivery_delay_days <= 0))
            total_rec = len(received_purchases)
            rec.on_time_delivery_rate = round((on_time / total_rec * 100), 2) if total_rec else 0.0

            reorder_rules = self.env['tapis.reorder.rule'].search([('state', '=', 'to_order')])
            rec.products_to_reorder = len(reorder_rules)
            rec.total_recommended_purchase_qty = sum(reorder_rules.mapped('qty_to_order'))

            rec.total_profit = sum(delivered_sales.mapped('profit_amount'))
            margins = delivered_sales.mapped('margin_percent')
            rec.average_margin_percent = sum(margins) / len(margins) if margins else 0.0

            customers = self.env['tapis.customer'].search([])
            rec.total_customer_receivables = sum(customers.mapped('current_balance'))

            raw_materials = self.env['tapis.raw.material'].search([])
            rec.raw_material_count = len(raw_materials)
            rec.raw_material_inventory_value = sum(raw_materials.mapped('inventory_value'))
            rec.low_raw_material_count = len(raw_materials.filtered(lambda m: m.stock_qty < 10))

            products_with_bom = self.env['tapis.product'].search([('bom_ids', '!=', False)])
            costs = products_with_bom.mapped('manufacturing_cost')
            rec.avg_manufacturing_cost = sum(costs) / len(costs) if costs else 0.0

            inspections = self.env['tapis.quality.inspection'].search([('state', '=', 'completed')])
            rec.total_quality_inspections = len(inspections)
            rec.passed_inspections = len(inspections.filtered(lambda i: i.result == 'passed'))
            rec.failed_inspections = len(inspections.filtered(lambda i: i.result == 'failed'))
            rec.quality_pass_rate = (
                (rec.passed_inspections / rec.total_quality_inspections * 100)
                if rec.total_quality_inspections else 0.0
            )

            invoices = self.env['tapis.invoice'].search([('state', '=', 'posted')])
            rec.total_invoices = len(invoices)
            rec.unpaid_invoices = len(invoices.filtered(lambda i: i.payment_status in ('unpaid', 'partial')))
            rec.total_invoice_amount = sum(invoices.mapped('amount_total'))
            rec.total_receivables_from_invoices = sum(invoices.mapped('amount_due'))

            equipment = self.env['tapis.equipment'].search([])
            rec.total_equipment = len(equipment)
            rec.broken_equipment_count = len(equipment.filtered(lambda e: e.state == 'broken'))
            rec.under_maintenance_equipment_count = len(equipment.filtered(lambda e: e.state == 'maintenance'))
            rec.total_equipment_maintenance_cost = sum(equipment.mapped('total_maintenance_cost'))
            rec.overdue_maintenance_count = len(equipment.filtered(lambda e: e.overdue_maintenance))
            rec.total_equipment_downtime = sum(equipment.mapped('total_downtime_hours'))
            projects = self.env['tapis.project'].search([])
            tasks = self.env['tapis.task'].search([])
            rec.total_projects = len(projects)
            rec.active_projects = len(projects.filtered(lambda p: p.state == 'in_progress'))
            rec.total_tasks = len(tasks)
            today = fields.Date.today()
            rec.overdue_tasks = len(tasks.filtered(
                lambda t: t.deadline and t.deadline < today and t.state not in ('done', 'cancelled')
            ))
            rec.tasks_in_review = len(tasks.filtered(lambda t: t.state == 'review'))
            rec.total_timesheet_hours = sum(tasks.mapped('actual_hours'))
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

            documents = self.env['tapis.document'].search([])
            rec.total_documents = len(documents)
            rec.expired_documents = len(documents.filtered(lambda d: d.is_expired))
            rec.documents_pending_approval = len(documents.filtered(lambda d: d.state == 'draft'))

            ApprovalReq = self.env['tapis.approval.request']
            all_reqs = ApprovalReq.search([])
            rec.pending_approvals = len(all_reqs.filtered(lambda r: r.state == 'pending'))
            today = fields.Date.today()
            today_start = fields.Datetime.to_datetime(today)
            rec.approvals_approved_today = len(all_reqs.filtered(
                lambda r: r.state == 'approved' and r.request_date and r.request_date >= today_start))
            rec.approvals_rejected_today = len(all_reqs.filtered(
                lambda r: r.state == 'rejected' and r.request_date and r.request_date >= today_start))
            completed = all_reqs.filtered(lambda r: r.state in ('approved', 'rejected'))
            times = []
            for req in completed:
                approved_lines = req.line_ids.filtered(lambda l: l.state == 'approved' and l.decision_date)
                if approved_lines:
                    first = approved_lines.sorted('decision_date')[:1]
                    if req.request_date:
                        delta = (first.decision_date - req.request_date).total_seconds() / 3600.0
                        times.append(delta)
            rec.average_approval_time = sum(times) / len(times) if times else 0.0

            CommLog = self.env['tapis.communication.log']
            rec.emails_sent_today = CommLog.search_count([('status', '=', 'sent'), ('sent_date', '>=', today_start)])
            rec.failed_emails = CommLog.search_count([('status', '=', 'failed')])
            rec.pending_notifications = CommLog.search_count([('status', '=', 'pending')])
            today = fields.Date.today()
            rec.overdue_alerts = self.env['tapis.invoice'].search_count([
                ('state', '=', 'posted'),
                ('payment_status', 'in', ('unpaid', 'partial')),
                ('due_date', '<', today),
            ])

            AutoJob = self.env['tapis.automation.job']
            all_jobs = AutoJob.search([])
            rec.total_automation_jobs = len(all_jobs)
            rec.active_jobs = len(all_jobs.filtered(lambda j: j.active))
            today_start = fields.Datetime.to_datetime(today)
            rec.failed_jobs_today = self.env['tapis.automation.job.log'].search_count([
                ('status', '=', 'failed'),
                ('start_datetime', '>=', today_start),
            ])
            completed_jobs = all_jobs.filtered(lambda j: j.total_runs > 0)
            rates = [j.success_rate for j in completed_jobs]
            rec.automation_success_rate = (
                sum(rates) / len(rates) if rates else 0.0
            )
            durations = [j.average_duration_seconds for j in completed_jobs]
            rec.average_job_duration = (
                sum(durations) / len(durations) if durations else 0.0
            )
            rec.pending_next_runs = len(all_jobs.filtered(
                lambda j: j.active and j.next_execution
            ))

            AuditLog = self.env['tapis.audit.log']
            rec.total_changes_today = AuditLog.search_count([
                ('action_date', '>=', today_start)
            ])
            models_group = AuditLog.search_read(
                [('action_date', '>=', today_start)],
                ['model_name'],
                order='id desc'
            )
            model_counts = {}
            for m in models_group:
                name = m['model_name']
                model_counts[name] = model_counts.get(name, 0) + 1
            rec.most_modified_model = max(model_counts, key=model_counts.get) if model_counts else ''
            user_ids = AuditLog.search([
                ('action_date', '>=', today_start)
            ]).mapped('user_id.id')
            rec.active_users_today = len(set(user_ids))
            rec.deletion_count = AuditLog.search_count([
                ('action_type', '=', 'unlink'),
                ('action_date', '>=', today_start),
            ])

            SigReq = self.env['tapis.signature.request']
            rec.pending_signatures = SigReq.search_count([('state', '=', 'pending')])
            rec.signed_today = SigReq.search_count([
                ('state', '=', 'signed'),
                ('request_date', '>=', today_start),
            ])
            rec.rejected_signatures = SigReq.search_count([('state', '=', 'rejected')])

            profiles = self.env['tapis.company.profile'].search([])
            rec.active_companies = len(profiles)
            rec.consolidated_revenue = sum(profiles.mapped('revenue_ytd'))
            rec.consolidated_profit = sum(profiles.mapped('net_profit_ytd'))
            rec.intercompany_transactions_count = self.env['tapis.intercompany.rule'].search_count([('active', '=', True)])

            SecurityIncident = self.env['tapis.security.incident']
            rec.security_incidents_today = SecurityIncident.search_count([
                ('incident_date', '>=', today_start)
            ])
            rec.blocked_access_attempts = SecurityIncident.search_count([
                ('incident_date', '>=', today_start),
                ('operation', 'in', ('export_blocked', 'unauthorized_access')),
            ])
            rec.high_severity_incidents = SecurityIncident.search_count([
                ('severity', 'in', ('high', 'critical')),
            ])
            rec.users_with_global_access = self.env['res.users'].search_count([
                ('data_access_scope', '=', 'global'),
                ('active', '=', True),
            ])

    def action_refresh(self):
        self.invalidate_cache()
        self._compute_dashboard()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tapis.dashboard',
            'view_mode': 'form',
            'view_id': self.env.ref('tapis_erp.view_dashboard_form').id,
            'target': 'current',
            'res_id': self.id,
        }

    def action_open_products(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products',
            'res_model': 'tapis.product',
            'view_mode': 'tree,form,kanban',
            'target': 'current',
        }

    def action_open_designs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Designs',
            'res_model': 'tapis.design',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_productions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Productions',
            'res_model': 'tapis.production',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_sales(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales',
            'res_model': 'tapis.sale',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_purchases(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchases',
            'res_model': 'tapis.purchase',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_suppliers(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Suppliers',
            'res_model': 'tapis.supplier',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_employees(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Employees',
            'res_model': 'tapis.employee',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_low_stock(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Low Stock Products',
            'res_model': 'tapis.product',
            'view_mode': 'tree,form,kanban',
            'domain': [('stock_qty', '<', 5)],
            'target': 'current',
        }

    def action_open_customers(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customers',
            'res_model': 'tapis.customer',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_reorder_rules(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reorder Rules',
            'res_model': 'tapis.reorder.rule',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'to_order')],
            'target': 'current',
        }

    def action_open_raw_materials(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Raw Materials',
            'res_model': 'tapis.raw.material',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_low_raw_materials(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Low Stock Raw Materials',
            'res_model': 'tapis.raw.material',
            'view_mode': 'tree,form',
            'domain': [('stock_qty', '<', 10)],
            'target': 'current',
        }

    def action_open_quality_inspections(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quality Inspections',
            'res_model': 'tapis.quality.inspection',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'tapis.invoice',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_equipment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Equipment',
            'res_model': 'tapis.equipment',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_maintenance_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance Orders',
            'res_model': 'tapis.maintenance.order',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_projects(self):
        return {'type': 'ir.actions.act_window', 'name': 'Projects', 'res_model': 'tapis.project', 'view_mode': 'kanban,tree,form', 'target': 'current'}
    def action_open_tasks(self):
        return {'type': 'ir.actions.act_window', 'name': 'Tasks', 'res_model': 'tapis.task', 'view_mode': 'kanban,tree,form', 'target': 'current'}
    def action_open_overdue_tasks(self):
        today = fields.Date.today()
        return {'type': 'ir.actions.act_window', 'name': 'Overdue Tasks', 'res_model': 'tapis.task', 'view_mode': 'tree,form', 'domain': [('deadline', '<', today.strftime('%Y-%m-%d')), ('state', 'not in', ('done', 'cancelled'))], 'target': 'current'}
    def action_open_broken_equipment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Broken Equipment',
            'res_model': 'tapis.equipment',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'broken')],
            'target': 'current',
        }

    def action_open_maintenance_equipment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Equipment Under Maintenance',
            'res_model': 'tapis.equipment',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'maintenance')],
            'target': 'current',
        }

    def action_open_unpaid_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Unpaid Invoices',
            'res_model': 'tapis.invoice',
            'view_mode': 'tree,form',
            'domain': [('payment_status', 'in', ('unpaid', 'partial'))],
            'target': 'current',
        }

    def action_open_audit_logs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Audit Logs',
            'res_model': 'tapis.audit.log',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_crm_pipeline(self):
        return {'type': 'ir.actions.act_window', 'name': 'CRM Pipeline', 'res_model': 'tapis.crm.lead', 'view_mode': 'kanban,tree,form', 'target': 'current'}

    def action_open_weighted_pipeline(self):
        leads = self.env['tapis.crm.lead'].search([('state', '=', 'open')])
        return {'type': 'ir.actions.act_window', 'name': 'Pipeline Opportunities', 'res_model': 'tapis.crm.lead', 'view_mode': 'kanban,tree,form', 'domain': [('id', 'in', leads.ids)], 'target': 'current'}

    def action_open_documents(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_expired_documents(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expired Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('is_expired', '=', True)],
            'target': 'current',
        }

    def action_open_pending_approval_documents(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents Pending Approval',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'draft')],
            'target': 'current',
        }

    def action_open_communication_logs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Communication Logs',
            'res_model': 'tapis.communication.log',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_signature_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Signature Requests',
            'res_model': 'tapis.signature.request',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_automation_jobs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Automation Jobs',
            'res_model': 'tapis.automation.job',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_approval_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approval Requests',
            'res_model': 'tapis.approval.request',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_company_profiles(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Company Profiles',
            'res_model': 'tapis.company.profile',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_security_incidents(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Security Incidents',
            'res_model': 'tapis.security.incident',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_designs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Designs',
            'res_model': 'tapis.design',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_closing_this_month(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1)
        return {'type': 'ir.actions.act_window', 'name': 'Closing This Month', 'res_model': 'tapis.crm.lead', 'view_mode': 'kanban,tree,form', 'domain': [('expected_closing_date', '>=', month_start.strftime('%Y-%m-%d')), ('expected_closing_date', '<', month_end.strftime('%Y-%m-%d')), ('state', '=', 'open')], 'target': 'current'}
