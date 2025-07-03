# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestMobileMoney(TransactionCase):

    def setUp(self):
        super(TestMobileMoney, self).setUp()
        self.partner_model = self.env['res.partner']

    def test_mobile_money_validation(self):
        """Test de validation des numéros Mobile Money"""
        partner = self.partner_model.create({
            'name': 'Test Partner',
            'mobile_money_operator': 'orange',
            'mobile_money_number': '+237 655 12 34 56'
        })

        # Numéro valide
        self.assertTrue(partner.id, "Le partenaire avec numéro valide doit être créé")

        # Numéro invalide
        with self.assertRaises(ValidationError):
            self.partner_model.create({
                'name': 'Test Partner 2',
                'mobile_money_operator': 'orange',
                'mobile_money_number': '+237 123 45 67 89'  # Format invalide
            })

    def test_cash_transfer_wizard(self):
        """Test du wizard de transfert de fonds"""
        # Créer des journaux de test
        cash_journal = self.env['account.journal'].create({
            'name': 'Caisse Test',
            'code': 'TEST_CASH',
            'type': 'cash',
        })

        bank_journal = self.env['account.journal'].create({
            'name': 'Banque Test',
            'code': 'TEST_BANK',
            'type': 'bank',
        })

        wizard = self.env['cash.transfer.wizard'].create({
            'name': 'Test Transfer',
            'transfer_type': 'cash_to_bank',
            'amount': 100000,
            'source_journal_id': cash_journal.id,
            'destination_journal_id': bank_journal.id,
        })

        # Exécuter le transfert
        result = wizard.action_transfer()
        self.assertTrue(result, "Le transfert doit réussir")

