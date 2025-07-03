# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # Journaux spécifiques camerounais
    cameroon_journal_type = fields.Selection([
        ('sales_cm', 'Ventes Cameroun'),
        ('purchase_cm', 'Achats Cameroun'),
        ('bank_cm', 'Banque Cameroun'),
        ('cash_cm', 'Caisse Cameroun'),
        ('mobile_money', 'Mobile Money'),
        ('miscellaneous_cm', 'Opérations diverses Cameroun')
    ], string='Type journal Cameroun')

    mobile_money_operator = fields.Selection([
        ('orange', 'Orange Money'),
        ('mtn', 'MTN Mobile Money'),
        ('express_union', 'Express Union Mobile'),
        ('campost', 'CamPost Mobile')
    ], string='Opérateur Mobile Money')

    # Configuration spécifique Cameroun
    use_cameroon_sequence = fields.Boolean(string='Utiliser séquence Cameroun', default=True)
    cameroon_bank_code = fields.Char(string='Code banque Cameroun', size=5)
    cameroon_agency_code = fields.Char(string='Code agence', size=5)

    @api.model
    def create_cameroon_default_journals(self):
        """Créer les journaux par défaut pour le Cameroun"""
        company = self.env.company

        journals_to_create = [
            {
                'name': 'Ventes',
                'code': 'VTE',
                'type': 'sale',
                'cameroon_journal_type': 'sales_cm',
            },
            {
                'name': 'Achats',
                'code': 'ACH', 
                'type': 'purchase',
                'cameroon_journal_type': 'purchase_cm',
            },
            {
                'name': 'Caisse FCFA',
                'code': 'CAI',
                'type': 'cash',
                'cameroon_journal_type': 'cash_cm',
            },
            {
                'name': 'Orange Money',
                'code': 'OMO',
                'type': 'bank',
                'cameroon_journal_type': 'mobile_money',
                'mobile_money_operator': 'orange',
            },
            {
                'name': 'MTN Mobile Money',
                'code': 'MTN',
                'type': 'bank', 
                'cameroon_journal_type': 'mobile_money',
                'mobile_money_operator': 'mtn',
            }
        ]

        created_journals = []
        for journal_data in journals_to_create:
            existing = self.search([('code', '=', journal_data['code']), ('company_id', '=', company.id)])
            if not existing:
                journal_data['company_id'] = company.id
                journal = self.create(journal_data)
                created_journals.append(journal)

        return created_journals
