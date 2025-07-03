# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAccountingChart(TransactionCase):

    def setUp(self):
        super(TestAccountingChart, self).setUp()
        self.company = self.env.ref('base.main_company')
        self.company.country_id = self.env.ref('base.cm')

    def test_syscohada_accounts_creation(self):
        """Test de création des comptes SYSCOHADA"""
        # Vérifier que les comptes principaux existent
        account_101 = self.env['account.account'].search([('code', '=', '101000')])
        self.assertTrue(account_101, "Le compte Capital doit exister")

        account_411 = self.env['account.account'].search([('code', '=', '411000')])
        self.assertTrue(account_411, "Le compte Clients doit exister")

        account_701 = self.env['account.account'].search([('code', '=', '701000')])
        self.assertTrue(account_701, "Le compte Ventes doit exister")

    def test_cameroon_taxes(self):
        """Test des taxes camerounaises"""
        # TVA 19,25%
        vat_tax = self.env['account.tax'].search([('name', 'like', '19,25%')])
        self.assertTrue(vat_tax, "La TVA 19,25% doit être configurée")

        if vat_tax:
            self.assertEqual(vat_tax[0].amount, 19.25, "Le taux de TVA doit être 19,25%")

    def test_mobile_money_accounts(self):
        """Test des comptes Mobile Money"""
        orange_account = self.env['account.account'].search([('code', '=', '573100')])
        self.assertTrue(orange_account, "Le compte Orange Money doit exister")

        mtn_account = self.env['account.account'].search([('code', '=', '573200')])
        self.assertTrue(mtn_account, "Le compte MTN Mobile Money doit exister")
