# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CashTransferWizard(models.TransientModel):
    _name = 'cash.transfer.wizard'
    _description = 'Assistant de Transfert de Fonds'

    name = fields.Char(string='Référence', required=True, default='Transfert')
    transfer_type = fields.Selection([
        ('cash_to_bank', 'Caisse vers Banque'),
        ('bank_to_cash', 'Banque vers Caisse'),
        ('mobile_money', 'Mobile Money'),
        ('bank_to_bank', 'Banque vers Banque')
    ], string='Type de transfert', required=True, default='cash_to_bank')

    amount = fields.Monetary(string='Montant', required=True, currency_field='currency_id')

    source_journal_id = fields.Many2one('account.journal', string='Journal source', required=True)
    destination_journal_id = fields.Many2one('account.journal', string='Journal destination', required=True)

    transfer_date = fields.Date(string='Date de transfert', default=fields.Date.today(), required=True)

    reference = fields.Char(string='Référence externe')
    memo = fields.Text(string='Notes')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    # Champs Mobile Money
    mobile_money_operator = fields.Selection([
        ('orange', 'Orange Money'),
        ('mtn', 'MTN Mobile Money'),
        ('express_union', 'Express Union Mobile'),
        ('campost', 'CamPost Mobile')
    ], string='Opérateur Mobile Money')

    mobile_number = fields.Char(string='Numéro Mobile Money')
    transaction_id = fields.Char(string='ID Transaction')

    @api.onchange('transfer_type')
    def _onchange_transfer_type(self):
        """Filtrer les journaux selon le type de transfert"""
        if self.transfer_type == 'cash_to_bank':
            source_domain = [('type', '=', 'cash')]
            dest_domain = [('type', '=', 'bank')]
        elif self.transfer_type == 'bank_to_cash':
            source_domain = [('type', '=', 'bank')]
            dest_domain = [('type', '=', 'cash')]
        elif self.transfer_type == 'mobile_money':
            source_domain = [('type', 'in', ['cash', 'bank'])]
            dest_domain = [('cameroon_journal_type', '=', 'mobile_money')]
        else:  # bank_to_bank
            source_domain = dest_domain = [('type', '=', 'bank')]

        return {
            'domain': {
                'source_journal_id': source_domain,
                'destination_journal_id': dest_domain
            }
        }

    def action_transfer(self):
        """Effectuer le transfert"""
        self.ensure_one()

        if self.amount <= 0:
            raise UserError(_("Le montant doit être positif"))

        if self.source_journal_id == self.destination_journal_id:
            raise UserError(_("Les journaux source et destination doivent être différents"))

        # Créer l'écriture de transfert
        move_vals = {
            'journal_id': self.source_journal_id.id,
            'date': self.transfer_date,
            'ref': self.name,
            'line_ids': [
                (0, 0, {
                    'name': f"Transfert vers {self.destination_journal_id.name}",
                    'account_id': self.destination_journal_id.default_account_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': f"Transfert depuis {self.source_journal_id.name}",
                    'account_id': self.source_journal_id.default_account_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                })
            ]
        }

        # Ajouter des informations Mobile Money si applicable
        if self.transfer_type == 'mobile_money':
            move_vals['ref'] += f" - {self.mobile_money_operator}"
            if self.transaction_id:
                move_vals['ref'] += f" - {self.transaction_id}"

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }
