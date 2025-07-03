# -*- coding: utf-8 -*-

"""Automatic tax reminder models."""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class TaxReminder(models.Model):
    _name = 'tax.reminder'
    """Store scheduled tax reminders."""
    _description = 'Rappel Fiscal Automatique'
    _order = 'due_date desc'

    name = fields.Char(string='Nom', required=True)
    tax_type = fields.Selection([
        ('vat', 'TVA Mensuelle'),
        ('corporate', 'Impôt sur les Sociétés'),
        ('cfc', 'Contribution Forfaitaire à la Charge Patronale'),
        ('tac', "Taxe d'Apprentissage"),
        ('municipal', 'Centimes Communaux'),
        ('dipe', 'DIPE'),
        ('dsf', 'DSF')
    ], string='Type de Taxe', default='vat')

    due_date = fields.Date(string="Date d'échéance", required=True)

    reminder_days = fields.Integer(
        string='Jours avant rappel',
        help="Nombre de jours avant l'échéance pour déclencher le rappel",
        default=7
    )

    active = fields.Boolean(string='Actif', default=True)

    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)

    state = fields.Selection([
        ('pending', 'En attente'),
        ('sent', 'Envoyé'),
        ('done', 'Terminé'),
        ('cancelled', 'Annulé')
    ], string='État', default='pending')

    last_reminder_date = fields.Date(string='Dernier rappel envoyé')

    @api.model
    def _send_reminders(self):
        """Envoi automatique des rappels fiscaux (appelé par CRON)"""
        today = date.today()

        reminders = self.search([
            ('active', '=', True),
            ('state', '=', 'pending'),
            ('due_date', '<=', today + timedelta(days=7))  # 7 jours avant
        ])

        for reminder in reminders:
            # Vérifier si l'échéance est proche
            days_until_due = (reminder.due_date - today).days

            if days_until_due <= reminder.reminder_days:
                reminder._send_notification()

    def _send_notification(self):
        """Envoi de notification par email"""
        self.ensure_one()

        template = self.env.ref('l10n_cm_accounting.tax_reminder_email_template', raise_if_not_found=False)

        if template:
            template.send_mail(self.id, force_send=True)

        # Créer une activité dans le chatter
        self.company_id.message_post(
            body=_("Rappel fiscal: %s - Échéance: %s") % (self.name, self.due_date),
            subject=_("Rappel Fiscal - %s") % self.name,
            message_type='notification'
        )

        self.state = 'sent'
        self.last_reminder_date = fields.Date.today()

        _logger.info(f"Rappel fiscal envoyé: {self.name} - Échéance: {self.due_date}")

    def action_mark_done(self):
        """Marquer comme terminé"""
        self.state = 'done'

    def action_cancel(self):
        """Annuler le rappel"""
        self.state = 'cancelled'

    @api.model
    def create_annual_reminders(self, year):
        """Créer les rappels annuels pour une année donnée"""
        annual_reminders = [
            {
                'name': f'TVA Janvier {year}',
                'tax_type': 'vat',
                'due_date': date(year, 2, 15),  # 15 février pour TVA janvier
            },
            {
                'name': f'TVA Février {year}',
                'tax_type': 'vat', 
                'due_date': date(year, 3, 15),
            },
            {
                'name': f'DIPE T1 {year}',
                'tax_type': 'dipe',
                'due_date': date(year, 4, 30),
            },
            {
                'name': f'DSF {year}',
                'tax_type': 'dsf',
                'due_date': date(year, 4, 30),
            },
            {
                'name': f'Impôt sur les Sociétés {year}',
                'tax_type': 'corporate',
                'due_date': date(year + 1, 3, 31),
            }
        ]

        created_reminders = []
        for reminder_data in annual_reminders:
            reminder = self.create(reminder_data)
            created_reminders.append(reminder)

        return created_reminders

