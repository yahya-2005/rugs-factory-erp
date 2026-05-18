"""Comprehensive test data loader for tapis_erp.
Run via: odoo-bin shell -d odoo -c odoo.conf
then: exec(open(path).read())
"""

from odoo import fields
import base64

now = fields.Datetime.now()

# Skip if already loaded
if env['tapis.product'].search_count([('code', '=', 'PRD-T001')]):
    print("=== TEST DATA ALREADY LOADED ===")
else:
    # Get companies
    company_maroc = env.ref('tapis_erp.company_tapis_maroc', raise_if_not_found=False)
    company_export = env.ref('tapis_erp.company_tapis_export', raise_if_not_found=False)
    if not company_maroc:
        company_maroc = env['res.company'].search([], limit=1)
    if not company_export:
        company_export = env['res.company'].search([('id', '!=', company_maroc.id)], limit=1) or company_maroc

    ctx_maroc = {'force_company': company_maroc.id}
    ctx_export = {'force_company': company_export.id}

    # Products
    p1 = env['tapis.product'].with_context(**ctx_maroc).create({
        'name': 'Atlas Diamond Carpet', 'code': 'PRD-T001',
        'category': 'traditional', 'price': 4500, 'cost': 2200, 'stock_qty': 25,
        'company_id': company_maroc.id,
    })
    p2 = env['tapis.product'].with_context(**ctx_maroc).create({
        'name': 'Modern Geometric', 'code': 'PRD-T002',
        'category': 'modern', 'price': 5800, 'cost': 3100, 'stock_qty': 12,
        'company_id': company_maroc.id,
    })
    p3 = env['tapis.product'].with_context(**ctx_maroc).create({
        'name': 'Silk Royal Premium', 'code': 'PRD-T003',
        'category': 'custom', 'price': 12000, 'cost': 6500, 'stock_qty': 5,
        'is_shared': True, 'company_id': company_maroc.id,
    })
    p4 = env['tapis.product'].with_context(**ctx_export).create({
        'name': 'Export Collection Wool', 'code': 'PRD-T004',
        'category': 'traditional', 'price': 3200, 'cost': 1500, 'stock_qty': 40,
        'company_id': company_export.id,
    })

    # Customers
    c1 = env['tapis.customer'].with_context(**ctx_maroc).create({
        'name': u'Paris Décor SARL', 'phone': '+33 1 23 45 67 89',
        'email': 'contact@parisdecor.fr', 'address': u'15 Rue de la Paix, Paris',
        'company_id': company_maroc.id,
    })
    c2 = env['tapis.customer'].with_context(**ctx_maroc).create({
        'name': 'Dubai Luxury Homes', 'phone': '+971 4 123 4567',
        'email': 'info@dubailuxury.ae', 'address': 'Sheikh Zayed Road, Dubai',
        'company_id': company_maroc.id,
    })
    c3 = env['tapis.customer'].with_context(**ctx_export).create({
        'name': 'Berlin Interiors GmbH', 'phone': '+49 30 9876 5432',
        'email': 'info@berlininteriors.de', 'address': 'Unter den Linden 25, Berlin',
        'company_id': company_export.id,
    })

    # Warehouses
    wh1 = env['tapis.warehouse'].with_context(**ctx_maroc).create({
        'name': 'Casablanca Main Warehouse',
        'code': 'WH-CASA',
        'address': 'Zone Industrielle, Casablanca',
        'company_id': company_maroc.id,
    })
    wh2 = env['tapis.warehouse'].with_context(**ctx_maroc).create({
        'name': u'Marrakech Workshop',
        'code': 'WH-MAR',
        'address': u'Quartier Industriel, Marrakech',
        'company_id': company_maroc.id,
    })
    wh3 = env['tapis.warehouse'].with_context(**ctx_export).create({
        'name': 'Berlin Distribution Center',
        'code': 'WH-BER',
        'address': 'Gewerbegebiet, Berlin',
        'company_id': company_export.id,
    })

    # Stock Quants
    env['tapis.stock.quant'].with_context(**ctx_maroc).create([
        {'product_id': p1.id, 'warehouse_id': wh1.id, 'quantity': 15, 'company_id': company_maroc.id},
        {'product_id': p1.id, 'warehouse_id': wh2.id, 'quantity': 10, 'company_id': company_maroc.id},
        {'product_id': p2.id, 'warehouse_id': wh1.id, 'quantity': 8, 'company_id': company_maroc.id},
    ])
    env['tapis.stock.quant'].with_context(**ctx_export).create([
        {'product_id': p4.id, 'warehouse_id': wh3.id, 'quantity': 30, 'company_id': company_export.id},
    ])

    # Sales
    s1 = env['tapis.sale'].with_context(**ctx_maroc).create({
        'name': 'SALE-T001',
        'customer_id': c1.id, 'product_id': p1.id,
        'warehouse_id': wh1.id,
        'quantity': 3, 'unit_price': 4500, 'state': 'confirmed',
        'company_id': company_maroc.id,
    })
    s2 = env['tapis.sale'].with_context(**ctx_maroc).create({
        'name': 'SALE-T002',
        'customer_id': c2.id, 'product_id': p3.id,
        'warehouse_id': wh1.id,
        'quantity': 2, 'unit_price': 12000, 'state': 'draft',
        'company_id': company_maroc.id,
    })
    s3 = env['tapis.sale'].with_context(**ctx_export).create({
        'name': 'SALE-T003',
        'customer_id': c3.id, 'product_id': p4.id,
        'warehouse_id': wh3.id,
        'quantity': 5, 'unit_price': 3200, 'state': 'delivered',
        'company_id': company_export.id,
    })

    # Purchases
    supplier_wool = env.ref('tapis_erp.supplier_maroc_wool', raise_if_not_found=False)
    supplier_textile = env.ref('tapis_erp.supplier_atlas_textiles', raise_if_not_found=False)
    if supplier_wool and supplier_textile:
        env['tapis.purchase'].with_context(**ctx_maroc).create([
            {'name': 'PUR-T001', 'supplier_id': supplier_wool.id, 'product_id': p1.id,
             'warehouse_id': wh1.id,
             'quantity': 50, 'unit_price': 2200, 'state': 'approved',
             'company_id': company_maroc.id},
            {'name': 'PUR-T002', 'supplier_id': supplier_textile.id, 'product_id': p2.id,
             'warehouse_id': wh1.id,
             'quantity': 20, 'unit_price': 3100, 'state': 'pending_approval',
             'company_id': company_maroc.id},
        ])

    # Invoices
    env['tapis.invoice'].with_context(**ctx_maroc).create({
        'name': 'INV-T001', 'sale_id': s1.id,
        'amount_untaxed': 13500, 'tax_rate': 20,
        'state': 'posted', 'payment_status': 'unpaid',
        'company_id': company_maroc.id,
    })
    env['tapis.invoice'].with_context(**ctx_export).create({
        'name': 'INV-T002', 'sale_id': s3.id,
        'amount_untaxed': 16000, 'tax_rate': 19,
        'state': 'posted', 'payment_status': 'paid',
        'company_id': company_export.id,
    })

    # Productions
    prod1 = env['tapis.production'].with_context(**ctx_maroc).create({
        'name': 'PROD-T001',
        'product_id': p1.id, 'quantity': 5,
        'warehouse_id': wh1.id,
        'state': 'planned', 'company_id': company_maroc.id,
    })
    prod2 = env['tapis.production'].with_context(**ctx_maroc).create({
        'name': 'PROD-T002',
        'product_id': p3.id, 'quantity': 2,
        'warehouse_id': wh2.id,
        'state': 'in_progress', 'company_id': company_maroc.id,
    })

    # Quality Inspections
    env['tapis.quality.inspection'].with_context(**ctx_maroc).create([
        {'name': 'QI-T001', 'product_id': p3.id, 'production_id': prod2.id, 'result': 'passed',
         'company_id': company_maroc.id},
        {'name': 'QI-T002', 'product_id': p1.id, 'production_id': prod1.id, 'result': 'failed',
         'company_id': company_maroc.id},
    ])

    # Equipment
    equip1 = env['tapis.equipment'].with_context(**ctx_maroc).create({
        'name': 'Jacquard Loom-01', 'category': 'loom', 'state': 'operational',
        'company_id': company_maroc.id,
    })
    equip2 = env['tapis.equipment'].with_context(**ctx_maroc).create({
        'name': 'Dyeing Machine-01', 'category': 'dyeing', 'state': 'maintenance',
        'company_id': company_maroc.id,
    })
    env['tapis.equipment'].with_context(**ctx_export).create({
        'name': 'CNC Cutter-01', 'category': 'cutting', 'state': 'operational',
        'company_id': company_export.id,
    })

    # Maintenance Orders
    env['tapis.maintenance.order'].with_context(**ctx_maroc).create({
        'equipment_id': equip2.id,
        'description': 'Routine maintenance of dyeing machine',
        'state': 'in_progress', 'company_id': company_maroc.id,
    })

    # Projects
    proj1 = env['tapis.project'].with_context(**ctx_maroc).create({
        'name': 'Hotel Royal Palace Project',
        'description': 'Supply and installation of carpets for Hotel Royal Palace',
        'state': 'in_progress', 'budget_amount': 250000,
        'company_id': company_maroc.id,
    })
    proj2 = env['tapis.project'].with_context(**ctx_export).create({
        'name': 'European Expansion Q2',
        'description': 'European market expansion project',
        'state': 'draft', 'budget_amount': 180000,
        'company_id': company_export.id,
    })

    # Tasks
    env['tapis.task'].with_context(**ctx_maroc).create([
        {'name': 'Design custom patterns for Hotel', 'project_id': proj1.id,
         'state': 'in_progress', 'planned_hours': 120,
         'company_id': company_maroc.id},
        {'name': 'Produce 50 carpets for Hotel', 'project_id': proj1.id,
         'state': 'todo', 'planned_hours': 400,
         'deadline': '2026-07-15', 'company_id': company_maroc.id},
    ])

    # CRM Leads
    env['tapis.crm.lead'].with_context(**ctx_maroc).create([
        {'name': 'Milan Design Store', 'expected_revenue': 75000,
         'probability': 60, 'state': 'open',
         'company_id': company_maroc.id},
        {'name': 'Casablanca Office Tower', 'expected_revenue': 95000,
         'probability': 100, 'state': 'won',
         'company_id': company_maroc.id},
    ])
    env['tapis.crm.lead'].with_context(**ctx_export).create([
        {'name': 'Barcelona Hotel Chain', 'expected_revenue': 120000,
         'probability': 40, 'state': 'open',
         'company_id': company_export.id},
    ])

    # Cost Centers
    cc1 = env['tapis.cost.center'].with_context(**ctx_maroc).create({
        'name': 'Production Department',
        'company_id': company_maroc.id,
    })
    env['tapis.cost.center'].with_context(**ctx_maroc).create({
        'name': 'Sales & Marketing',
        'company_id': company_maroc.id,
    })

    # Budgets
    env['tapis.budget'].with_context(**ctx_maroc).create({
        'cost_center_id': cc1.id,
        'fiscal_year': 2026, 'state': 'approved',
        'company_id': company_maroc.id,
    })

    # Document Folders
    doc_folder = env['tapis.document.folder'].with_context(**ctx_maroc).create({
        'name': 'Certifications',
        'company_id': company_maroc.id,
    })
    # Documents
    dummy_pdf = base64.b64encode(b'%PDF-1.4 dummy pdf content for test')
    env['tapis.document'].with_context(**ctx_maroc).create([
        {'name': 'Quality Certificate ISO 9001', 'folder_id': doc_folder.id,
         'attachment': dummy_pdf, 'state': 'approved',
         'company_id': company_maroc.id},
        {'name': 'Export Contract EU-2026', 'folder_id': doc_folder.id,
         'attachment': dummy_pdf, 'state': 'draft',
         'is_shared': True, 'company_id': company_maroc.id},
    ])

    # Approval Category + Rule + Request
    app_cat = env['tapis.approval.category'].with_context(**ctx_maroc).create({
        'name': 'Budget Approvals', 'code': 'CAT-BUDGET',
        'model_name': 'tapis.purchase',
        'company_id': company_maroc.id,
    })
    env.cr.execute("""
        INSERT INTO tapis_approval_rule (name, category_id, min_amount, max_amount, required_approvals, active, company_id, create_uid, create_date, write_uid, write_date)
        VALUES (%s, %s, %s, %s, %s, true, %s, %s, NOW(), %s, NOW())
        RETURNING id
    """, ['Manager Budget Approval', app_cat.id, 10000, 100000, 1, company_maroc.id, env.user.id, env.user.id])
    app_rule_id = env.cr.fetchone()[0]
    env.cr.execute(
        'INSERT INTO res_users_tapis_approval_rule_rel (tapis_approval_rule_id, res_users_id) VALUES (%s, %s)',
        [app_rule_id, env.user.id]
    )
    app_rule = env['tapis.approval.rule'].browse(app_rule_id)
    env['tapis.approval.request'].with_context(**ctx_maroc).create({
        'category_id': app_cat.id,
        'reference_model': 'tapis.purchase', 'reference_id': 1,
        'requested_by': env.user.id,
        'amount': 50000,
        'state': 'pending', 'company_id': company_maroc.id,
    })

    # Signature Template + Request
    sig_template = env['tapis.signature.template'].with_context(**ctx_maroc).create({
        'name': 'Standard Contract Template',
        'code': 'SIG-CONTRACT',
        'model_name': 'tapis.sale',
        'company_id': company_maroc.id,
    })
    env['tapis.signature.request'].with_context(**ctx_maroc).create({
        'template_id': sig_template.id,
        'reference_model': 'tapis.sale', 'reference_id': s1.id,
        'requested_by_id': env.user.id,
        'state': 'pending', 'company_id': company_maroc.id,
    })

    # Communication Logs
    env['tapis.communication.log'].with_context(**ctx_maroc).create({
        'name': 'Welcome email to Paris D\u00e9cor', 'status': 'sent',
        'company_id': company_maroc.id,
    })

    # Automation Jobs
    env['tapis.automation.job'].with_context(**ctx_maroc).create({
        'name': 'Daily Stock Report', 'code': 'AUTO-T001',
        'model_name': 'tapis.stock.quant',
        'method_name': 'action_check_low_stock',
        'company_id': company_maroc.id,
    })

    # Audit Logs
    env['tapis.audit.log'].with_context(**ctx_maroc).create([
        {'name': 'Created product Atlas Diamond', 'model_name': 'tapis.product',
         'record_id': p1.id, 'user_id': env.user.id,
         'action_type': 'create', 'company_id': company_maroc.id},
        {'name': 'Updated sale order Paris', 'model_name': 'tapis.sale',
         'record_id': s1.id, 'user_id': env.user.id,
         'action_type': 'write', 'company_id': company_maroc.id},
    ])

    # Stock Moves
    env['tapis.stock.move'].with_context(**ctx_maroc).create({
        'name': 'SM-T001',
        'product_id': p1.id,
        'source_warehouse_id': wh2.id,
        'destination_warehouse_id': wh1.id,
        'quantity': 5,
        'company_id': company_maroc.id,
    })

    # Customer Payments
    env['tapis.customer.payment'].with_context(**ctx_maroc).create({
        'name': 'PAY-T001',
        'customer_id': c1.id, 'amount': 13500,
        'company_id': company_maroc.id,
    })

    # Security
    env['tapis.security.incident'].create({
        'name': 'Test: Unauthorized access attempt',
        'model_name': 'tapis.budget',
        'operation': 'unauthorized_access',
        'severity': 'medium',
    })
    env['tapis.security.department'].create([
        {'name': 'IT Security', 'code': 'SEC-IT',
         'description': 'Information technology security team'},
        {'name': 'Financial Control', 'code': 'SEC-FIN',
         'description': 'Financial security and compliance'},
    ])

    env.cr.commit()
    print("=== TEST DATA LOADED SUCCESSFULLY ===")
    print(f"  Products: {env['tapis.product'].search_count([])}")
    print(f"  Customers: {env['tapis.customer'].search_count([])}")
    print(f"  Warehouses: {env['tapis.warehouse'].search_count([])}")
    print(f"  Stock Quants: {env['tapis.stock.quant'].search_count([])}")
    print(f"  Sales: {env['tapis.sale'].search_count([])}")
    print(f"  Purchases: {env['tapis.purchase'].search_count([])}")
    print(f"  Invoices: {env['tapis.invoice'].search_count([])}")
    print(f"  Productions: {env['tapis.production'].search_count([])}")
    print(f"  Quality Inspections: {env['tapis.quality.inspection'].search_count([])}")
    print(f"  Equipment: {env['tapis.equipment'].search_count([])}")
    print(f"  Maintenance Orders: {env['tapis.maintenance.order'].search_count([])}")
    print(f"  Projects: {env['tapis.project'].search_count([])}")
    print(f"  Tasks: {env['tapis.task'].search_count([])}")
    print(f"  CRM Leads: {env['tapis.crm.lead'].search_count([])}")
    print(f"  Cost Centers: {env['tapis.cost.center'].search_count([])}")
    print(f"  Budgets: {env['tapis.budget'].search_count([])}")
    print(f"  Documents: {env['tapis.document'].search_count([])}")
    print(f"  Approval Requests: {env['tapis.approval.request'].search_count([])}")
    print(f"  Signature Requests: {env['tapis.signature.request'].search_count([])}")
    print(f"  Communication Logs: {env['tapis.communication.log'].search_count([])}")
    print(f"  Automation Jobs: {env['tapis.automation.job'].search_count([])}")
    print(f"  Audit Logs: {env['tapis.audit.log'].search_count([])}")
    print(f"  Stock Moves: {env['tapis.stock.move'].search_count([])}")
    print(f"  Customer Payments: {env['tapis.customer.payment'].search_count([])}")
    print(f"  Security Incidents: {env['tapis.security.incident'].search_count([])}")
    print(f"  Security Departments: {env['tapis.security.department'].search_count([])}")
