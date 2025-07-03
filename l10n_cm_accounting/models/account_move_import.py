# -*- coding: utf-8 -*-

"""Wizard to import accounting moves from Excel."""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import pandas as pd
import base64
import io
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class AccountMoveImport(models.TransientModel):
    _name = 'account.move.import'
    """Import wizard handling Excel files."""
    _description = "Assistant d'importation d'écritures comptables"

    name = fields.Char(string="Nom de l'importation", required=True, default=lambda self: "Import du " + datetime.today().strftime('%d/%m/%Y'))
    import_file = fields.Binary(string="Fichier Excel", required=True, help="Fichier Excel contenant les écritures à importer")
    filename = fields.Char(string="Nom du fichier")
    journal_id = fields.Many2one('account.journal', string="Journal par défaut", help="Journal utilisé si non spécifié dans le fichier")
    import_state = fields.Selection([
        ('draft', 'Brouillon'),
        ('imported', 'Importé'),
        ('error', 'Erreur')
    ], string="État", default='draft')
    error_log = fields.Text(string="Log d'erreurs")
    success_count = fields.Integer(string="Nombre d'écritures créées", default=0)
    error_count = fields.Integer(string="Nombre d'erreurs", default=0)
    preview_data = fields.Text(string="Aperçu des données")

    def action_download_template(self):
        """Télécharge un template Excel pré-formaté"""
        # Créer un DataFrame avec les colonnes requises
        template_data = {
            'Date': ['2025-01-15', '2025-01-15'],
            'Journal': ['VTE', 'VTE'],
            'Compte': ['411000', '701000'],
            'Libelle': ['Vente de marchandises', 'Vente de marchandises'],
            'Debit': [1192500, 0],
            'Credit': [0, 1000000],
            'Reference': ['VTE001', 'VTE001'],
            'Tiers': ['CUSTOMER_001', ''],
            'Exercice_Fiscal': ['2025', '2025']
        }

        df = pd.DataFrame(template_data)

        # Créer le fichier Excel en mémoire
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Ecritures', index=False)

            # Formater le fichier
            workbook = writer.book
            worksheet = writer.sheets['Ecritures']

            # Format des en-têtes
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BC',
                'border': 1
            })

            # Appliquer le format aux en-têtes
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # Ajuster la largeur des colonnes
            worksheet.set_column('A:I', 15)

            # Ajouter des commentaires
            worksheet.write_comment('A1', 'Format: AAAA-MM-JJ')
            worksheet.write_comment('B1', 'Code du journal (ex: VTE, ACH, BQ1)')
            worksheet.write_comment('C1', 'Numéro de compte SYSCOHADA')
            worksheet.write_comment('E1', 'Montant débit en FCFA')
            worksheet.write_comment('F1', 'Montant crédit en FCFA')

        excel_data = output.getvalue()

        # Créer l'attachement
        attachment = self.env['ir.attachment'].create({
            'name': 'template_import_ecritures.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_preview_import(self):
        """Aperçu des données avant importation"""
        if not self.import_file:
            raise UserError(_("Veuillez sélectionner un fichier à importer."))

        try:
            # Décoder le fichier
            file_data = base64.b64decode(self.import_file)
            df = pd.read_excel(io.BytesIO(file_data))

            # Valider les colonnes requises
            required_columns = ['Date', 'Journal', 'Compte', 'Libelle', 'Debit', 'Credit']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                raise UserError(_("Colonnes manquantes dans le fichier: %s") % ', '.join(missing_columns))

            # Aperçu des premières lignes
            preview = df.head(10).to_html(classes='table table-striped', table_id='preview_table')
            self.preview_data = preview

            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'show_preview': True}
            }

        except Exception as e:
            raise UserError(_("Erreur lors de la lecture du fichier: %s") % str(e))

    def action_import_moves(self):
        """Import des écritures depuis le fichier Excel"""
        if not self.import_file:
            raise UserError(_("Veuillez sélectionner un fichier à importer."))

        self.success_count = 0
        self.error_count = 0
        error_messages = []

        try:
            # Décoder et lire le fichier
            file_data = base64.b64decode(self.import_file)
            df = pd.read_excel(io.BytesIO(file_data))

            # Validation des colonnes
            required_columns = ['Date', 'Journal', 'Compte', 'Libelle', 'Debit', 'Credit']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                raise UserError(_("Colonnes manquantes: %s") % ', '.join(missing_columns))

            # Nettoyer les données
            df = df.dropna(subset=['Date', 'Compte'])
            df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
            df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)

            # Grouper par référence pour créer les écritures
            grouped = df.groupby(df['Reference'].fillna(df.index))

            for ref, group in grouped:
                try:
                    self._create_move_from_group(group)
                    self.success_count += 1
                except Exception as e:
                    self.error_count += 1
                    error_messages.append(f"Référence {ref}: {str(e)}")
                    _logger.error(f"Erreur import écriture {ref}: {e}")

            # Mise à jour du statut
            if self.error_count == 0:
                self.import_state = 'imported'
                message = _("Import réussi: %d écritures créées") % self.success_count
            else:
                self.import_state = 'error'
                message = _("Import partiel: %d réussies, %d erreurs") % (self.success_count, self.error_count)

            self.error_log = '\n'.join(error_messages) if error_messages else ''

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success' if self.error_count == 0 else 'warning',
                    'sticky': True,
                }
            }

        except Exception as e:
            self.import_state = 'error'
            self.error_log = str(e)
            raise UserError(_("Erreur lors de l'import: %s") % str(e))

    def _create_move_from_group(self, group):
        """Créer une écriture comptable à partir d'un groupe de lignes"""
        if group.empty:
            raise UserError(_("Groupe vide"))

        first_row = group.iloc[0]

        # Validation de base
        if pd.isna(first_row['Date']):
            raise UserError(_("Date manquante"))

        # Conversion de la date
        move_date = self._parse_date(first_row['Date'])

        # Journal
        journal = self._get_journal(first_row.get('Journal', ''))
        if not journal:
            journal = self.journal_id
        if not journal:
            raise UserError(_("Journal non spécifié"))

        # Exercice fiscal (gestion directe sans dépendance externe)
        fiscal_year = self._get_or_create_fiscal_year(move_date)

        # Validation équilibre débit/crédit
        total_debit = group['Debit'].sum()
        total_credit = group['Credit'].sum()

        if abs(total_debit - total_credit) > 0.01:
            raise UserError(_("Écriture déséquilibrée: Débit=%.2f, Crédit=%.2f") % (total_debit, total_credit))

        # Créer l'écriture
        move_vals = {
            'journal_id': journal.id,
            'date': move_date,
            'ref': str(first_row.get('Reference', '')),
            'line_ids': []
        }

        # Créer les lignes d'écriture
        for _, row in group.iterrows():
            account = self._get_account(row['Compte'])
            if not account:
                raise UserError(_("Compte %s introuvable") % row['Compte'])

            partner = self._get_partner(row.get('Tiers', '')) if row.get('Tiers') else False

            line_vals = {
                'account_id': account.id,
                'name': str(row['Libelle']),
                'debit': float(row['Debit']),
                'credit': float(row['Credit']),
                'partner_id': partner.id if partner else False,
            }
            move_vals['line_ids'].append((0, 0, line_vals))

        # Créer l'écriture
        move = self.env['account.move'].create(move_vals)
        return move

    def _parse_date(self, date_value):
        """Parser une date depuis différents formats"""
        if isinstance(date_value, datetime):
            return date_value.date()
        elif isinstance(date_value, date):
            return date_value
        elif isinstance(date_value, str):
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    return datetime.strptime(date_value, fmt).date()
                except ValueError:
                    continue
            raise UserError(_("Format de date invalide: %s") % date_value)
        else:
            raise UserError(_("Type de date invalide: %s") % type(date_value))

    def _get_journal(self, journal_code):
        """Récupérer un journal par son code"""
        if not journal_code:
            return False
        return self.env['account.journal'].search([('code', '=', journal_code)], limit=1)

    def _get_account(self, account_code):
        """Récupérer un compte par son code"""
        if not account_code:
            return False
        return self.env['account.account'].search([('code', '=', str(account_code))], limit=1)

    def _get_partner(self, partner_ref):
        """Récupérer un partenaire par sa référence"""
        if not partner_ref:
            return False
        return self.env['res.partner'].search([
            '|', ('ref', '=', partner_ref), ('name', 'ilike', partner_ref)
        ], limit=1)

    def _get_or_create_fiscal_year(self, move_date):
        """Retourne ou crée un cm.fiscal.year couvrant la date donnée."""
        company = self.env.company
        fiscal_year = self.env['cm.fiscal.year'].search([
            ('company_id', '=', company.id),
            ('date_start', '<=', move_date),
            ('date_end', '>=', move_date),
        ], limit=1)

        if not fiscal_year:
            year = move_date.year
            fiscal_year = self.env['cm.fiscal.year'].create({
                'name': str(year),
                'date_start': date(year, 1, 1),
                'date_end': date(year, 12, 31),
                'company_id': company.id,
            })

        return fiscal_year

    @api.model
    def get_import_statistics(self):
        """Statistiques des imports récents"""
        domain = [('create_date', '>=', fields.Datetime.now().replace(hour=0, minute=0, second=0))]
        imports = self.search(domain)

        return {
            'total_imports': len(imports),
            'successful_imports': len(imports.filtered(lambda x: x.import_state == 'imported')),
            'failed_imports': len(imports.filtered(lambda x: x.import_state == 'error')),
            'total_moves_created': sum(imports.mapped('success_count')),
        }

