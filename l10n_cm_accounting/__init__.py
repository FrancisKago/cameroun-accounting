# -*- coding: utf-8 -*-
from . import models
from . import wizards

def _l10n_cm_post_init_hook(cr, registry):
    """Post installation hook for Cameroon localization"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Configure company defaults
    companies = env['res.company'].search([])
    for company in companies:
        if company.country_id and company.country_id.code == 'CM':
            vals = {}
            try:
                vals['currency_id'] = env.ref('base.XAF').id
            except Exception:
                pass
            try:
                vals['account_fiscal_country_id'] = env.ref('base.cm').id
            except Exception:
                pass
            if vals:
                company.write(vals)
