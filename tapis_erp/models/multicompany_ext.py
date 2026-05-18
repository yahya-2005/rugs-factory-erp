from odoo import models, fields


class TapisProduct(models.Model):
    _inherit = 'tapis.product'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)
    is_shared = fields.Boolean(string='Shared Across Companies', default=False)


class TapisDesign(models.Model):
    _inherit = 'tapis.design'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)
    is_shared = fields.Boolean(string='Shared Across Companies', default=False)


class TapisCustomer(models.Model):
    _inherit = 'tapis.customer'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)
    is_shared = fields.Boolean(string='Shared Across Companies', default=False)


class TapisSupplier(models.Model):
    _inherit = 'tapis.supplier'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)
    is_shared = fields.Boolean(string='Shared Across Companies', default=False)


class TapisSale(models.Model):
    _inherit = 'tapis.sale'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisPurchase(models.Model):
    _inherit = 'tapis.purchase'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisInvoice(models.Model):
    _inherit = 'tapis.invoice'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisProduction(models.Model):
    _inherit = 'tapis.production'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisWarehouse(models.Model):
    _inherit = 'tapis.warehouse'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisStockQuant(models.Model):
    _inherit = 'tapis.stock.quant'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisStockMove(models.Model):
    _inherit = 'tapis.stock.move'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisBom(models.Model):
    _inherit = 'tapis.bom'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisBomLine(models.Model):
    _inherit = 'tapis.bom.line'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisQualityInspection(models.Model):
    _inherit = 'tapis.quality.inspection'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisEquipment(models.Model):
    _inherit = 'tapis.equipment'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisMaintenanceOrder(models.Model):
    _inherit = 'tapis.maintenance.order'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisProject(models.Model):
    _inherit = 'tapis.project'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisProjectTag(models.Model):
    _inherit = 'tapis.project.tag'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisTask(models.Model):
    _inherit = 'tapis.task'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisTaskTimesheet(models.Model):
    _inherit = 'tapis.task.timesheet'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisCrmLead(models.Model):
    _inherit = 'tapis.crm.lead'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisBudget(models.Model):
    _inherit = 'tapis.budget'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisBudgetLine(models.Model):
    _inherit = 'tapis.budget.line'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisDocument(models.Model):
    _inherit = 'tapis.document'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)
    is_shared = fields.Boolean(string='Shared Across Companies', default=False)


class TapisApprovalRequest(models.Model):
    _inherit = 'tapis.approval.request'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisApprovalRequestLine(models.Model):
    _inherit = 'tapis.approval.request.line'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisSignatureRequest(models.Model):
    _inherit = 'tapis.signature.request'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisSignatureRequestLine(models.Model):
    _inherit = 'tapis.signature.request.line'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisCommunicationLog(models.Model):
    _inherit = 'tapis.communication.log'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisAutomationJob(models.Model):
    _inherit = 'tapis.automation.job'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisAuditLog(models.Model):
    _inherit = 'tapis.audit.log'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisEmployee(models.Model):
    _inherit = 'tapis.employee'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisTag(models.Model):
    _inherit = 'tapis.tag'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisDocumentFolder(models.Model):
    _inherit = 'tapis.document.folder'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisCrmStage(models.Model):
    _inherit = 'tapis.crm.stage'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisCostCenter(models.Model):
    _inherit = 'tapis.cost.center'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisSupplierPricelist(models.Model):
    _inherit = 'tapis.supplier.pricelist'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisReorderRule(models.Model):
    _inherit = 'tapis.reorder.rule'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisStockTransfer(models.Model):
    _inherit = 'tapis.stock.transfer'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisRawMaterial(models.Model):
    _inherit = 'tapis.raw.material'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisCustomerPayment(models.Model):
    _inherit = 'tapis.customer.payment'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisCommunicationTemplate(models.Model):
    _inherit = 'tapis.communication.template'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisSignatureTemplate(models.Model):
    _inherit = 'tapis.signature.template'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisSignatureRole(models.Model):
    _inherit = 'tapis.signature.role'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisApprovalCategory(models.Model):
    _inherit = 'tapis.approval.category'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)


class TapisApprovalRule(models.Model):
    _inherit = 'tapis.approval.rule'
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company, required=True)
