# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from datetime import date


class TestFiscalDeclarations(TransactionCase):

    def setUp(self):
        super(TestFiscalDeclarations, self).setUp()
        self.company = self.env.ref('base.main_company')
        self.declaration_wizard = self.env['fiscal.declaration.wizard']

    def test_dsf_declaration(self):
        """Test de génération DSF"""
        wizard = self.declaration_wizard.create({
            'name': 'Test DSF 2025',
            'declaration_type': 'dsf',
            'fiscal_year': 2025,
            'date_from': date(2025, 1, 1),
            'date_to': date(2025, 12, 31),
        })

        wizard.action_compute_declaration()
        self.assertEqual(wizard.state, 'computed', "La DSF doit être calculée")

    def test_dipe_declaration(self):
        """Test de calcul DIPE"""
        wizard = self.declaration_wizard.create({
            'name': 'Test DIPE Q1 2025',
            'declaration_type': 'dipe',
            'fiscal_year': 2025,
            'date_from': date(2025, 1, 1),
            'date_to': date(2025, 3, 31),
        })

        wizard.action_compute_declaration()
        self.assertEqual(wizard.state, 'computed', "La DIPE doit être calculée")

        # Vérifier que le taux DIPE de 2,2% est appliqué
        if wizard.total_sales > 0:
            expected_dipe = wizard.total_sales * 0.022
            self.assertEqual(wizard.corporate_tax, expected_dipe, "Le calcul DIPE doit être correct")

