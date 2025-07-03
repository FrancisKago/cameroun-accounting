# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = "account.asset"

    asset_number = fields.Char(
        string="Numéro d'immobilisation",
        help="Numéro unique d'identification de l'immobilisation"
    )

    acquisition_mode = fields.Selection([
        ("purchase", "Achat"),
        ("production", "Production"),
        ("donation", "Don/Subvention"),
        ("exchange", "Échange"),
        ("contribution", "Apport en nature")
    ], string="Mode d'acquisition", default="purchase")

    supplier_id = fields.Many2one(
        "res.partner",
        string="Fournisseur",
        domain=[("supplier_rank", ">", 0)]
    )

    purchase_date = fields.Date(
        string="Date d'acquisition",
        help="Date d'acquisition de l'immobilisation"
    )

    warranty_start_date = fields.Date(string="Début de garantie")
    warranty_end_date = fields.Date(string="Fin de garantie")

    location = fields.Char(
        string="Localisation",
        help="Lieu où se trouve l'immobilisation"
    )

    responsible_id = fields.Many2one(
        "hr.employee",
        string="Responsable",
        help="Employé responsable de l'immobilisation"
    )

    insurance_policy = fields.Char(
        string="Police d'assurance",
        help="Numéro de police d'assurance"
    )

    maintenance_contract = fields.Char(
        string="Contrat de maintenance",
        help="Référence du contrat de maintenance"
    )

    # Champs spécifiques SYSCOHADA
    syscohada_category = fields.Selection([
        ('21', 'Immobilisations incorporelles'),
        ('22', 'Terrains'),
        ('23', 'Bâtiments, installations techniques'),
        ('24', 'Matériel'),
        ('26', 'Titres de participation'),
        ('27', 'Autres immobilisations financières')
    ], string="Catégorie SYSCOHADA")

    cameroon_depreciation_method = fields.Selection([
        ('linear', 'Linéaire'),
        ('declining', 'Dégressif'),
        ('accelerated', 'Accéléré (fiscalement)')
    ], string="Méthode d'amortissement Cameroun", default='linear')

    tax_depreciation_rate = fields.Float(
        string="Taux fiscal d'amortissement (%)",
        help="Taux d'amortissement autorisé fiscalement au Cameroun"
    )

    @api.model
    def create(self, vals):
        """Générer automatiquement un numéro d'immobilisation"""
        if not vals.get("asset_number"):
            sequence = self.env["ir.sequence"].next_by_code("account.asset.number")
            if not sequence:
                # Créer la séquence si elle n'existe pas
                self.env["ir.sequence"].sudo().create({
                    "name": "Numéro Immobilisation",
                    "code": "account.asset.number",
                    "prefix": "IMM/",
                    "suffix": "",
                    "padding": 5,
                    "number_increment": 1,
                    "implementation": "standard"
                })
                sequence = self.env["ir.sequence"].next_by_code("account.asset.number")
            vals["asset_number"] = sequence
        return super().create(vals)

    @api.onchange('syscohada_category')
    def _onchange_syscohada_category(self):
        """Proposer les taux d'amortissement selon SYSCOHADA"""
        if self.syscohada_category:
            depreciation_rates = {
                '21': 20,  # Immobilisations incorporelles: 5 ans
                '22': 0,   # Terrains: non amortissables
                '23': 5,   # Bâtiments: 20 ans
                '24': 25,  # Matériel: 4 ans
                '26': 0,   # Titres de participation: non amortissables
                '27': 10   # Autres immobilisations financières: 10 ans
            }

            rate = depreciation_rates.get(self.syscohada_category, 0)
            if rate > 0:
                self.tax_depreciation_rate = rate
                self.method_number = int(100 / rate)  # Durée en années

    def action_generate_depreciation_schedule(self):
        """Générer le tableau d'amortissement selon les normes camerounaises"""
        self.ensure_one()
        if not self.original_value or not self.method_number:
            raise UserError(_("Veuillez définir la valeur et la durée d'amortissement"))
        if not self.first_depreciation_date:
            raise UserError(_("Veuillez définir la date de première dotation d'amortissement"))

        # Supprimer les lignes existantes non validées
        self.depreciation_move_ids.filtered(lambda x: x.state == "draft").unlink()

        # Calcul selon le système linéaire (SYSCOHADA)
        annual_depreciation = self.original_value / self.method_number

        for year in range(int(self.method_number)):
            depreciation_date = date(self.first_depreciation_date.year + year, 12, 31)

            # Créer l'écriture d'amortissement
            move_vals = {
                "ref": f"Amortissement {self.name} - Année {year + 1}",
                "date": depreciation_date,
                "journal_id": self.journal_id.id,
                "line_ids": [
                    (0, 0, {
                        "name": f"Dotation amortissement {self.name}",
                        "account_id": self.account_depreciation_expense_id.id,
                        "debit": annual_depreciation,
                        "credit": 0.0,
                        "asset_id": self.id,
                    }),
                    (0, 0, {
                        "name": f"Amortissement cumulé {self.name}",
                        "account_id": self.account_depreciation_id.id,
                        "debit": 0.0,
                        "credit": annual_depreciation,
                        "asset_id": self.id,
                    })
                ]
            }
            self.env["account.move"].create(move_vals)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _("Tableau d'amortissement généré avec succès"),
                "type": "success",
            }
        }
