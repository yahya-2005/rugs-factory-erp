# Tapis ERP System

A comprehensive Enterprise Resource Planning (ERP) system designed specifically for **Tapis Moroccan carpet company**, built on the Odoo 15 framework.

## 📋 Project Overview

**Tapis ERP** is a fully-featured ERP module that streamlines all aspects of carpet manufacturing and distribution operations. It integrates sales, procurement, production, inventory management, human resources, CRM, project management, and advanced business intelligence features into a single, unified platform.

## 🎯 Main Objectives

- **Sales Management**: Manage customer orders, sales pipelines, and customer relationships
- **Production Planning**: BOM management, production scheduling, and order tracking
- **Inventory Control**: Real-time stock tracking, warehouse management, and reorder rules
- **Quality Assurance**: Quality inspection and compliance tracking
- **Procurement**: Supplier management, purchase orders, and pricing
- **HR Management**: Employee management and task timesheets
- **CRM System**: Lead management and sales pipeline tracking
- **Project Management**: Project planning, task management, and resource allocation
- **Financial Management**: Invoicing, budgeting, cost centers, and profitability analysis
- **Document Management**: Centralized document storage and organization
- **Security & Compliance**: Role-based access control, security policies, and audit logging
- **Automation**: Automated workflows and job scheduling
- **Multi-Company Support**: Handle multiple company entities with intercompany transactions
- **Advanced Reporting**: Comprehensive dashboards and business intelligence reports
- **Electronic Signatures**: Digital signature workflows and approvals
- **Communication**: Automated email templates and communication logs

## 🚀 Features

### Core Modules
- **Sales**: Quote management, sales orders, and customer profiles
- **Purchase**: Purchase requisitions, supplier management, and vendor scorecards
- **Stock**: Inventory tracking, warehouse management, stock transfers
- **Production**: BOM (Bill of Materials), production orders, design management
- **Accounting**: Invoicing, financial reporting, payment tracking
- **CRM**: Lead management, sales stages, pipeline analytics
- **HR**: Employee records, task assignments, timesheet tracking
- **Projects**: Project management with task tracking and resource planning

### Advanced Features
- **Approval Workflows**: Configurable approval rules and audit trails
- **Automation Engine**: Scheduled jobs and automated task execution
- **AI Integration**: AI-powered analysis and insights
- **Quality Management**: Inspection templates and compliance tracking
- **Security Module**: Department management, security policies, incident tracking
- **Analytics Dashboard**: Real-time KPIs and business metrics
- **Electronic Signatures**: Digital signature requests and verification
- **Document Management**: Folder structure and document organization

## 💻 Technical Stack

- **Framework**: Odoo 15
- **Language**: Python
- **Database**: PostgreSQL (Odoo standard)
- **Template Engine**: XML-based views and reports
- **Localization**: Multi-language support (English, French)

## 📦 Installation & Setup

### Prerequisites
- **Odoo 15** installed and configured
- PostgreSQL database
- Python 3.8+
- Git (for cloning the repository)

### Step-by-Step Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/tapis_erp.git
   cd tapis_erp
   ```

2. **Place the Module in Your Odoo Addons Directory**
   ```bash
   # Copy the tapis_erp folder to your Odoo addons folder
   cp -r tapis_erp /path/to/odoo/addons/
   ```
   
   Or if you're in a custom addons folder:
   ```bash
   cp -r tapis_erp /path/to/custom_addons/
   ```

3. **Update the Addons List**
   - Restart the Odoo service (if running)
   - Go to **Apps** menu in Odoo
   - Click **Update Apps List**
   - Search for "Tapis ERP"

4. **Install the Module**
   - Click on the **Tapis ERP** module in the Apps list
   - Click **Install**

5. **Load Demo Data (Optional)**
   - After installation, you can load demo data by activating "Load Sample Data" during module configuration
   - This will populate your database with sample customers, products, and transactions for testing

### Configuration

After installation, configure the following:

1. **Company Settings**
   - Go to **Settings** > **Companies** and set up your company profile
   - Configure company details, addresses, and logo

2. **Security & Access Control**
   - Define user roles and security groups
   - Set up record rules for data access control
   - Configure security policies

3. **Warehouse & Locations**
   - Set up warehouse locations and stock transfer routes
   - Configure reorder rules for inventory management

4. **Suppliers & Customers**
   - Add suppliers to the system
   - Configure customer payment terms
   - Set up supplier pricelists

5. **Production Settings**
   - Create Bills of Materials (BOM)
   - Configure production workflows
   - Set up equipment and maintenance orders

## 🔧 Usage Guide

### For Sales Team
1. **Create Sales Quotes**: Navigate to **Sales** > **Quotations** > **New**
2. **Manage Customer Orders**: Track order status and delivery schedules
3. **View CRM Pipeline**: Use **CRM** > **Pipeline** for sales forecasting

### For Production Team
1. **Create Production Orders**: Go to **Production** > **Manufacturing Orders**
2. **Manage BOM**: Configure bills of materials in **Production** > **BOM**
3. **Quality Inspection**: Log quality checks in **Quality** > **Inspections**

### For Inventory Team
1. **Monitor Stock Levels**: View inventory in **Stock** > **Stock On Hand**
2. **Process Stock Transfers**: Use **Stock** > **Transfers**
3. **Manage Reorder Rules**: Set minimum stock levels in **Stock** > **Reorder Rules**

### For Finance Team
1. **Generate Reports**: Access financial reports in **Reports** section
2. **Manage Budgets**: Create and track budgets in **Finance** > **Budgets**
3. **View Dashboards**: Analyze KPIs in **Dashboard** > **Analytics Dashboard**

### For HR Team
1. **Manage Employees**: Navigate to **HR** > **Employees**
2. **Track Timesheets**: Log hours in **HR** > **Timesheets**
3. **Assign Tasks**: Create tasks in **Tasks** > **New**

## 📊 Key Reports

- **Sales Report**: Revenue and order analytics
- **Production Report**: Manufacturing efficiency and output
- **Purchase Report**: Procurement analysis and supplier performance
- **Quality Report**: Inspection results and compliance
- **Profitability Report**: Margin analysis by product/customer
- **Customer Statement**: Payment and transaction history
- **Supplier Scorecard**: Vendor performance metrics
- **CRM Pipeline Report**: Sales forecast and funnel analysis
- **Project Report**: Project status and resource utilization
- **Audit Report**: System access and activity logs

## 🔐 Security Features

- **Role-Based Access Control (RBAC)**: Define user permissions by role
- **Record-Level Security**: Control access to specific records
- **Audit Logging**: Track all system activities
- **Electronic Signatures**: Secure digital approval workflows
- **Security Policies**: Enforce compliance requirements
- **Incident Management**: Report and track security incidents

## 🌍 Localization

The module supports multiple languages:
- **English (en_US)**
- **French (fr_FR)**

Additional languages can be added by creating translation files in the `i18n/` directory.

## 📁 Project Structure

```
tapis_erp/
├── __init__.py                 # Module initialization
├── __manifest__.py             # Module metadata and dependencies
├── models/                     # Business logic and data models
│   ├── sale.py                 # Sales management
│   ├── purchase.py             # Purchase management
│   ├── production.py           # Production orders
│   ├── bom.py                  # Bill of materials
│   ├── stock.py                # Inventory management
│   ├── customer.py             # Customer profiles
│   ├── supplier.py             # Supplier management
│   ├── crm_lead.py             # CRM leads
│   ├── project.py              # Project management
│   ├── hr.py                   # Human resources
│   ├── quality_inspection.py   # Quality control
│   ├── approval_request.py     # Approval workflows
│   ├── audit_log.py            # Audit trail
│   └── ... (other models)
├── views/                      # UI definitions (XML)
│   ├── sale_views.xml          # Sales interface
│   ├── production_views.xml    # Production interface
│   ├── stock_views.xml         # Inventory interface
│   ├── dashboard_views.xml     # Dashboard interface
│   └── ... (other views)
├── report/                     # Report definitions
│   ├── sale_report.xml         # Sales report
│   ├── production_report.xml   # Production report
│   └── ... (other reports)
├── data/                       # Demo and configuration data
│   ├── sequences.xml           # Document sequences
│   ├── company_demo_data.xml   # Sample companies
│   └── ... (other data files)
├── security/                   # Security and access control
│   ├── security.xml            # Security groups
│   ├── ir.model.access.csv     # Model access rules
│   └── record_rules.xml        # Record-level rules
├── i18n/                       # Translations
│   ├── en_US.po                # English translations
│   └── fr_FR.po                # French translations
└── static/                     # Static assets (CSS, JS, images)
```

## 🐛 Troubleshooting

### Module Installation Issues
- **Module not appearing in Apps list**: Ensure the folder is in the correct addons directory and restart Odoo
- **Dependency errors**: Install all required base modules: `base`, `mail`, `sale`, `purchase`, `stock`, `account`

### Data Loading Issues
- **Demo data not loading**: Check that all dependencies are installed
- **Missing translations**: Ensure language is installed in **Settings** > **Translations**

### Permission Issues
- **Access denied errors**: Check user security groups in **Settings** > **Users & Companies**
- **Record visibility issues**: Review record rules in **Settings** > **Security** > **Record Rules**

## 🤝 Contributing

To contribute improvements:
1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes and test thoroughly
3. Commit with clear messages: `git commit -m "Add feature description"`
4. Push to your branch: `git push origin feature/your-feature-name`
5. Submit a pull request for review

## 📝 License

This project is proprietary software for Tapis Moroccan Carpet Company. All rights reserved.

## 👨‍💼 Author

**Yahya Laadam**

## 📞 Support & Contact

For questions, issues, or feature requests, please contact the development team or create an issue in the project repository.

---

**Version**: 17.0.1.0  
**Last Updated**: 2026  
**Odoo Version**: Odoo 15+
