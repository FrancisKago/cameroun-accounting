# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta
import base64
import logging

_logger = logging.getLogger(__name__)


class FiscalDeclarationWizard(models.TransientModel):
    _name = 'fiscal.declaration.wizard'
    _description = "Assistant de Déclarations Fiscales Camerounaises"

    name = fields.Char(string="Nom de la déclaration", required=True)
    declaration_type = fields.Selection([
        ('dsf', "Déclaration Statistique et Fiscale (DSF)"),
        ('dipe', "Déclaration d'Impôt Provisionnel des Entreprises (DIPE)"),
        ('is', "Impôt sur les Sociétés (IS)"),
        ('vat_monthly', 'Déclaration TVA Mensuelle'),
        ('withholding_tax', 'Déclaration Retenues à la Source')
    ], string="Type de déclaration", required=True, default='dsf')

    period_type = fields.Selection([
        ('monthly', 'Mensuelle'),
        ('quarterly', 'Trimestrielle'),
        ('annual', 'Annuelle')
    ], string="Périodicité", default='monthly')

    fiscal_year = fields.Integer(
        string="Exercice fiscal",
        default=lambda self: datetime.now().year,
        required=True
    )

    period_month = fields.Selection([
        ('01', 'Janvier'), ('02', 'Février'), ('03', 'Mars'),
        ('04', 'Avril'), ('05', 'Mai'), ('06', 'Juin'),
        ('07', 'Juillet'), ('08', 'Août'), ('09', 'Septembre'),
        ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre')
    ], string="Mois")

    period_quarter = fields.Selection([
        ('Q1', '1er Trimestre'), ('Q2', '2ème Trimestre'),
        ('Q3', '3ème Trimestre'), ('Q4', '4ème Trimestre')
    ], string="Trimestre")

    date_from = fields.Date(string="Date de début", required=True)
    date_to = fields.Date(string="Date de fin", required=True)

    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
        required=True
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('computed', 'Calculé'),
        ('generated', 'Généré'),
        ('submitted', 'Soumis')
    ], string="État", default='draft')

    # Résultats calculés
    total_sales = fields.Monetary(string="Total des ventes", currency_field='currency_id')
    total_purchases = fields.Monetary(string="Total des achats", currency_field='currency_id')
    vat_collected = fields.Monetary(string="TVA collectée", currency_field='currency_id')
    vat_paid = fields.Monetary(string="TVA payée", currency_field='currency_id')
    vat_due = fields.Monetary(string="TVA due", currency_field='currency_id')
    withholding_tax = fields.Monetary(string="Retenues à la source", currency_field='currency_id')
    corporate_tax = fields.Monetary(string="Impôt sur les sociétés", currency_field='currency_id')

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

    report_data = fields.Text(string="Données du rapport")
    pdf_file = fields.Binary(string="Fichier PDF")
    pdf_filename = fields.Char(string="Nom du fichier PDF")

    @api.onchange('declaration_type')
    def _onchange_declaration_type(self):
        """Adapter la périodicité selon le type de déclaration"""
        if self.declaration_type == 'vat_monthly':
            self.period_type = 'monthly'
        elif self.declaration_type in ['dsf', 'is']:
            self.period_type = 'annual'
        elif self.declaration_type == 'dipe':
            self.period_type = 'quarterly'

    @api.onchange('period_type', 'fiscal_year', 'period_month', 'period_quarter')
    def _onchange_period(self):
        """Calculer automatiquement les dates de début et fin"""
        if not self.fiscal_year:
            return

        if self.period_type == 'annual':
            self.date_from = date(self.fiscal_year, 1, 1)
            self.date_to = date(self.fiscal_year, 12, 31)
        elif self.period_type == 'monthly' and self.period_month:
            month = int(self.period_month)
            self.date_from = date(self.fiscal_year, month, 1)
            if month == 12:
                self.date_to = date(self.fiscal_year, 12, 31)
            else:
                next_month = date(self.fiscal_year, month + 1, 1)
                self.date_to = date(next_month.year, next_month.month, 1).replace(day=1) - timedelta(days=1)
        elif self.period_type == 'quarterly' and self.period_quarter:
            quarter_months = {
                'Q1': (1, 3), 'Q2': (4, 6),
                'Q3': (7, 9), 'Q4': (10, 12)
            }
            start_month, end_month = quarter_months[self.period_quarter]
            self.date_from = date(self.fiscal_year, start_month, 1)
            if end_month == 12:
                self.date_to = date(self.fiscal_year, 12, 31)
            else:
                self.date_to = date(self.fiscal_year, end_month + 1, 1) - timedelta(days=1)

    def action_compute_declaration(self):
        """Calculer les montants de la déclaration"""
        self.ensure_one()

        if self.declaration_type == 'dsf':
            self._generate_dsf_declaration()
        elif self.declaration_type == 'dipe':
            self._generate_dipe_declaration()
        elif self.declaration_type == 'is':
            self._generate_is_declaration()
        elif self.declaration_type == 'vat_monthly':
            self._generate_vat_declaration()
        elif self.declaration_type == 'withholding_tax':
            self._generate_withholding_declaration()

        self.state = 'computed'

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_results': True}
        }

    def _generate_dsf_declaration(self):
        """Générer la Déclaration Statistique et Fiscale (DSF)"""
        # Récupérer les données comptables pour la période
        domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted')
        ]

        moves = self.env['account.move'].search(domain)

        # Calculs pour DSF
        sales_accounts = self.env['account.account'].search([
            ('code', '=like', '7%'),  # Comptes de produits SYSCOHADA
            ('company_id', '=', self.company_id.id)
        ])

        purchase_accounts = self.env['account.account'].search([
            ('code', '=like', '6%'),  # Comptes de charges SYSCOHADA
            ('company_id', '=', self.company_id.id)
        ])

        # Calculer le chiffre d'affaires (classe 7)
        sales_lines = moves.line_ids.filtered(
            lambda l: l.account_id in sales_accounts and l.credit > 0
        )
        self.total_sales = sum(sales_lines.mapped('credit'))

        # Calculer les achats (classe 6)
        purchase_lines = moves.line_ids.filtered(
            lambda l: l.account_id in purchase_accounts and l.debit > 0
        )
        self.total_purchases = sum(purchase_lines.mapped('debit'))

        # TVA collectée (compte 443)
        vat_collected_account = self.env['account.account'].search([
            ('code', '=', '443000'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if vat_collected_account:
            vat_collected_lines = moves.line_ids.filtered(
                lambda l: l.account_id == vat_collected_account and l.credit > 0
            )
            self.vat_collected = sum(vat_collected_lines.mapped('credit'))

        # TVA payée (compte 445)
        vat_paid_account = self.env['account.account'].search([
            ('code', '=', '445000'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if vat_paid_account:
            vat_paid_lines = moves.line_ids.filtered(
                lambda l: l.account_id == vat_paid_account and l.debit > 0
            )
            self.vat_paid = sum(vat_paid_lines.mapped('debit'))

        self.vat_due = self.vat_collected - self.vat_paid

        _logger.info(f"DSF calculée - CA: {self.total_sales}, Achats: {self.total_purchases}, TVA due: {self.vat_due}")

    def _generate_dipe_declaration(self):
        """Générer la Déclaration d'Impôt Provisionnel des Entreprises (DIPE)"""
        # DIPE est basé sur le CA du trimestre précédent
        # Taux standard: 2,2% du CA

        # Calculer le CA du trimestre
        sales_domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted')
        ]

        moves = self.env['account.move'].search(sales_domain)

        # Comptes de ventes (classe 7)
        sales_accounts = self.env['account.account'].search([
            ('code', '=like', '7%'),
            ('company_id', '=', self.company_id.id)
        ])

        sales_lines = moves.line_ids.filtered(
            lambda l: l.account_id in sales_accounts and l.credit > 0
        )
        self.total_sales = sum(sales_lines.mapped('credit'))

        # Calcul DIPE: 2,2% du CA trimestriel
        dipe_rate = 0.022
        self.corporate_tax = self.total_sales * dipe_rate

        _logger.info(f"DIPE calculée - CA trimestre: {self.total_sales}, DIPE: {self.corporate_tax}")

    def _generate_is_declaration(self):
        """Générer la déclaration d'Impôt sur les Sociétés (IS)"""
        # IS annuel: 30% pour les grandes entreprises, 25% pour les PME

        # Calculer le résultat fiscal
        profit_loss_accounts = self.env['account.account'].search([
            ('code', 'in', ['131000', '129000']),  # Bénéfice/Perte
            ('company_id', '=', self.company_id.id)
        ])

        moves_domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted')
        ]

        moves = self.env['account.move'].search(moves_domain)

        # Calculer le résultat comptable
        income_accounts = self.env['account.account'].search([
            ('code', '=like', '7%'),
            ('company_id', '=', self.company_id.id)
        ])

        expense_accounts = self.env['account.account'].search([
            ('code', '=like', '6%'),
            ('company_id', '=', self.company_id.id)
        ])

        # Total des produits
        income_lines = moves.line_ids.filtered(
            lambda l: l.account_id in income_accounts and l.credit > 0
        )
        total_income = sum(income_lines.mapped('credit'))

        # Total des charges
        expense_lines = moves.line_ids.filtered(
            lambda l: l.account_id in expense_accounts and l.debit > 0
        )
        total_expenses = sum(expense_lines.mapped('debit'))

        # Résultat comptable
        accounting_result = total_income - total_expenses

        # Déterminer le taux IS selon la taille de l'entreprise
        # PME (CA < 1 milliard): 25%, Grandes entreprises: 30%
        if self.total_sales < 1000000000:
            is_rate = 0.25  # 25% pour PME
        else:
            is_rate = 0.30  # 30% pour grandes entreprises

        # IS = Résultat fiscal * Taux
        # (Simplification: résultat fiscal = résultat comptable)
        if accounting_result > 0:
            self.corporate_tax = accounting_result * is_rate
        else:
            self.corporate_tax = 0

        self.total_sales = total_income
        self.total_purchases = total_expenses

        _logger.info(f"IS calculé - Résultat: {accounting_result}, IS: {self.corporate_tax}")

    def _generate_vat_declaration(self):
        """Générer la déclaration TVA mensuelle"""
        # Récupérer les mouvements de TVA
        moves_domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted')
        ]

        moves = self.env['account.move'].search(moves_domain)

        # TVA collectée (compte 443)
        vat_collected_account = self.env['account.account'].search([
            ('code', '=like', '443%'),
            ('company_id', '=', self.company_id.id)
        ])

        vat_collected_lines = moves.line_ids.filtered(
            lambda l: l.account_id in vat_collected_account and l.credit > 0
        )
        self.vat_collected = sum(vat_collected_lines.mapped('credit'))

        # TVA déductible (compte 445)
        vat_deductible_account = self.env['account.account'].search([
            ('code', '=like', '445%'),
            ('company_id', '=', self.company_id.id)
        ])

        vat_deductible_lines = moves.line_ids.filtered(
            lambda l: l.account_id in vat_deductible_account and l.debit > 0
        )
        self.vat_paid = sum(vat_deductible_lines.mapped('debit'))

        # TVA nette due
        self.vat_due = self.vat_collected - self.vat_paid

        _logger.info(f"TVA mensuelle - Collectée: {self.vat_collected}, Déductible: {self.vat_paid}, Due: {self.vat_due}")

    def _generate_withholding_declaration(self):
        """Générer la déclaration des retenues à la source"""
        # Rechercher les retenues effectuées
        withholding_accounts = self.env['account.account'].search([
            ('code', '=like', '421%'),  # Comptes de retenues
            ('company_id', '=', self.company_id.id)
        ])

        moves_domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted')
        ]

        moves = self.env['account.move'].search(moves_domain)

        withholding_lines = moves.line_ids.filtered(
            lambda l: l.account_id in withholding_accounts and l.credit > 0
        )

        self.withholding_tax = sum(withholding_lines.mapped('credit'))

        _logger.info(f"Retenues à la source: {self.withholding_tax}")

    def action_generate_pdf(self):
        """Générer le PDF de la déclaration"""
        self.ensure_one()

        if self.state != 'computed':
            raise UserError(_("Veuillez d'abord calculer la déclaration."))

        # Générer le rapport PDF selon le type
        report_name = f'l10n_cm_accounting.report_{self.declaration_type}'

        try:
            pdf = self.env.ref(report_name)._render_qweb_pdf([self.id])
            self.pdf_file = base64.b64encode(pdf[0])
            self.pdf_filename = f"{self.declaration_type}_{self.fiscal_year}_{self.id}.pdf"
            self.state = 'generated'

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/?model={self._name}&id={self.id}&field=pdf_file&download=true&filename={self.pdf_filename}',
                'target': 'self',
            }
        except Exception as e:
            _logger.error(f"Erreur génération PDF: {e}")
            raise UserError(_("Erreur lors de la génération du PDF: %s") % str(e))

    def action_submit_declaration(self):
        """Marquer la déclaration comme soumise"""
        self.ensure_one()

        if self.state != 'generated':
            raise UserError(_("Veuillez d'abord générer le PDF de la déclaration."))

        self.state = 'submitted'

        # Log dans le chatter
        self.company_id.message_post(
            body=_("Déclaration %s soumise pour la période %s - %s") % 
                 (dict(self._fields['declaration_type'].selection)[self.declaration_type],
                  self.date_from, self.date_to)
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _("Déclaration soumise avec succès"),
                'type': 'success',
            }
        }
