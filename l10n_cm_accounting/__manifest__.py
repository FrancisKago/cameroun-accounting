{
    'name': 'Cameroon - Accounting (SYSCOHADA)',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Localizations/Account Charts',
    'summary': 'Cameroon Accounting Localization for SYSCOHADA standard',
    'description': '''
Cameroon Accounting Localization
===============================

This module provides:
- Complete SYSCOHADA Chart of Accounts
- Cameroon Tax Configuration (VAT 19.25%, Withholding taxes)
- Fiscal declarations (DSF, DIPE, IS)
- Asset management with Cameroon depreciation rules
- Budget control and management
- Automated tax reminders
- Mobile Money integration (Orange Money, MTN Mobile Money)
- Import/Export facilities for accounting entries

Features:
- SYSCOHADA compliant chart of accounts
- Cameroon tax rates and fiscal positions
- Financial reports adapted to Cameroon regulations
- Automated fiscal year management
- Multi-currency support with FCFA as base currency
- Complete test suite for production readiness
    ''',
    'author': 'Francis Kago',
    'website': 'https://github.com/FrancisKago/Cameroun-accounting',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'analytic',
        'account_asset',
        'purchase',
        'point_of_sale',
        'base_import',
        'mail',
    ],
    'external_dependencies': {
        'python': ['pandas', 'xlrd', 'xlsxwriter'],
    },
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data files - order is important
        'data/account_chart_template_data.xml',
        'data/account.account.template.xml', 
        'data/account_tax_template_data.xml',
        # 'data/account_financial_report_data.xml',  # à fournir ou supprimer
        'data/tax_reminder_email_template.xml',
        'report/account_reports.xml',
        'data/ir_cron_data.xml',

        # Views
        'views/account_move_import_views.xml',
        'views/account_asset_views.xml',
        'views/account_budget_views.xml',
        'views/account_journal_views.xml',
        'views/res_partner_views.xml',
        'views/tax_reminder_views.xml',
        'views/pos_config_views.xml',

        # Wizards
        'wizards/declaration_wizard_views.xml',
        'wizards/cash_transfer_wizard_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'assets': {
        # 'point_of_sale.assets': [
        #     'l10n_cm_accounting/static/src/js/pos_credit_limit.js',
        # ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_l10n_cm_post_init_hook',
}
