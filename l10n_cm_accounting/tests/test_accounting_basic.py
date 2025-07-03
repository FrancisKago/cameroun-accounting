# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestAccountingBasic(TransactionCase):
    def test_create_budget(self):
        budget = self.env['account.budget'].create({
            'name': 'Test Budget',
            'fiscal_year': 2025,
        })
        self.assertTrue(budget)
        self.assertEqual(budget.name, 'Test Budget')

    def test_create_journal(self):
        journal = self.env['account.journal'].create({
            'name': 'Test Journal',
            'code': 'TJ01',
            'type': 'general',
            'company_id': self.env.company.id,
        })
        self.assertTrue(journal)
        self.assertEqual(journal.code, 'TJ01')

    def test_import_move(self):
        # Test minimal: just check wizard instantiation
        wizard = self.env['account.move.import'].create({
            'name': 'Import Test',
            'import_file': '',
            'filename': 'test.xlsx',
        })
        self.assertTrue(wizard)

