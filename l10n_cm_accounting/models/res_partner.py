# -*- coding: utf-8 -*-

"""Partner extensions for Cameroon."""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class ResPartner(models.Model):
    _inherit = "res.partner"
    """Add Cameroon-specific partner data."""

    # Informations fiscales camerounaises
    taxpayer_identifier = fields.Char(
        string="Numéro de Contribuable",
        size=15,
        help="Numéro d'identification du contribuable au Cameroun (Format: P + 9 chiffres + 1 lettre)"
    )

    commerce_registry = fields.Char(
        string="Registre de Commerce",
        size=40,
        help="Numéro d'inscription au registre de commerce"
    )

    tax_regime = fields.Selection([
        ('reel_normal', 'Réel Normal'),
        ('reel_simplifie', 'Réel Simplifié'),
        ('synthese', 'Synthèse'),
        ('forfaitaire', 'Forfaitaire'),
        ('liberatoire', 'Libératoire')
    ], string="Régime Fiscal", help="Régime fiscal applicable au partenaire")

    activity_sector = fields.Selection([
        ('primary', 'Secteur Primaire'),
        ('secondary', 'Secteur Secondaire'),
        ('tertiary', 'Secteur Tertiaire'),
        ('public', 'Secteur Public'),
        ('agriculture', 'Agriculture'),
        ('manufacturing', 'Industrie'),
        ('services', 'Services'),
        ('commerce', 'Commerce'),
        ('transport', 'Transport'),
        ('education', 'Éducation'),
        ('health', 'Santé'),
        ('finance', 'Finance'),
        ('telecoms', 'Télécommunications'),
        ('energy', 'Énergie'),
        ('construction', 'BTP'),
        ('mining', 'Mines'),
        ('tourism', 'Tourisme')
    ], string="Secteur d'activité", help="Secteur d'activité principal")

    # Champs spécifiques Mobile Money
    mobile_money_operator = fields.Selection([
        ('orange', 'Orange Money'),
        ('mtn', 'MTN Mobile Money'),
        ('express_union', 'Express Union Mobile'),
        ('campost', 'CamPost Mobile')
    ], string="Opérateur Mobile Money")

    mobile_money_number = fields.Char(
        string="Numéro Mobile Money",
        help="Numéro de téléphone pour les paiements Mobile Money"
    )

    # Informations bancaires spécifiques
    bank_account_type = fields.Selection([
        ('savings', "Compte d'épargne"),
        ('current', 'Compte courant'),
        ('fixed_deposit', 'Dépôt à terme'),
        ('foreign_currency', 'Compte devises')
    ], string="Type de compte bancaire")

    # Informations géographiques camerounaises
    region_cm = fields.Selection([
        ('adamaoua', 'Adamaoua'),
        ('centre', 'Centre'),
        ('est', 'Est'),
        ('extreme_nord', 'Extrême-Nord'),
        ('littoral', 'Littoral'),
        ('nord', 'Nord'),
        ('nord_ouest', 'Nord-Ouest'),
        ('ouest', 'Ouest'),
        ('sud', 'Sud'),
        ('sud_ouest', 'Sud-Ouest')
    ], string="Région du Cameroun")

    # Statut fiscal
    is_tax_exempt = fields.Boolean(
        string="Exonéré d'impôts",
        help="Cocher si le partenaire bénéficie d'exonérations fiscales"
    )

    tax_exemption_reason = fields.Text(
        string="Motif d'exonération",
        help="Détails sur les exonérations fiscales accordées"
    )

    # Seuils fiscaux
    annual_turnover = fields.Monetary(
        string="Chiffre d'affaires annuel",
        currency_field='currency_id',
        help="Chiffre d'affaires annuel déclaré (pour détermination du régime fiscal)"
    )

    vat_threshold_exceeded = fields.Boolean(
        string="Seuil TVA dépassé",
        compute='_compute_vat_threshold_exceeded',
        store=True,
        help="Indique si le seuil de 50 millions FCFA pour la TVA est dépassé"
    )

    @api.depends('annual_turnover')
    def _compute_vat_threshold_exceeded(self):
        """Calculer si le seuil TVA de 50 millions FCFA est dépassé"""
        for partner in self:
            partner.vat_threshold_exceeded = partner.annual_turnover > 50000000

    @api.constrains('taxpayer_identifier')
    def _check_taxpayer_identifier(self):
        """Validation du format du numéro de contribuable camerounais"""
        for partner in self:
            if partner.taxpayer_identifier:
                # Format camerounais: P + 9 chiffres + 1 lettre (ex: P123456789A)
                pattern = r'^P\d{9}[A-Z]$'
                if not re.match(pattern, partner.taxpayer_identifier.upper()):
                    raise ValidationError(
                        _("Le numéro de contribuable doit respecter le format: "
                          "P + 9 chiffres + 1 lettre (ex: P123456789A)")
                    )

    @api.constrains('mobile_money_number', 'mobile_money_operator')
    def _check_mobile_money_number(self):
        """Validation du numéro Mobile Money"""
        for partner in self:
            if partner.mobile_money_number and partner.mobile_money_operator:
                # Format camerounais: +237 XXXXXXXXX ou 6XXXXXXXX ou 5XXXXXXXX
                number = partner.mobile_money_number.replace(' ', '').replace('-', '')

                # Vérifier le format camerounais (accepte 6, 5, 2, 3, 4, 7, 8 selon opérateurs)
                if not re.match(r'^(\+237|237)?[2563478]\d{7,8}$', number):
                    raise ValidationError(
                        _("Le numéro Mobile Money doit être un numéro camerounais valide "
                          "(format: +237 XXXXXXXXX)")
                    )

    @api.constrains('annual_turnover')
    def _check_annual_turnover(self):
        """Validation du chiffre d'affaires"""
        for partner in self:
            if partner.annual_turnover < 0:
                raise ValidationError(_("Le chiffre d'affaires ne peut pas être négatif"))

    @api.model
    def get_tax_regime_thresholds(self):
        """Retourner les seuils pour les régimes fiscaux camerounais"""
        return {
            'vat_threshold': 50000000,  # 50 millions FCFA
            'forfaitaire_max': 15000000,  # 15 millions FCFA
            'synthese_max': 100000000,  # 100 millions FCFA
            'reel_simplifie_max': 1000000000,  # 1 milliard FCFA
        }

    def action_compute_recommended_tax_regime(self):
        """Calculer le régime fiscal recommandé basé sur le CA"""
        thresholds = self.get_tax_regime_thresholds()

        for partner in self:
            ca = partner.annual_turnover

            if ca <= thresholds['forfaitaire_max']:
                recommended = 'forfaitaire'
            elif ca <= thresholds['synthese_max']:
                recommended = 'synthese'
            elif ca <= thresholds['reel_simplifie_max']:
                recommended = 'reel_simplifie'
            else:
                recommended = 'reel_normal'

            partner.message_post(
                body=_("Régime fiscal recommandé: %s (basé sur CA: %s FCFA)") % 
                     (dict(partner._fields['tax_regime'].selection)[recommended], 
                      f"{ca:,.0f}")
            )

    def get_mobile_money_config(self):
        """Configuration pour les paiements Mobile Money"""
        self.ensure_one()

        if not self.mobile_money_operator or not self.mobile_money_number:
            return False

        configs = {
            'orange': {
                'api_url': 'https://api.orange.cm/mobile-money',
                'merchant_code': 'OM_MERCHANT',
                'service_code': '201'
            },
            'mtn': {
                'api_url': 'https://api.mtn.cm/mobile-money', 
                'merchant_code': 'MTN_MERCHANT',
                'service_code': '301'
            },
            'express_union': {
                'api_url': 'https://api.expressunion.cm/mobile',
                'merchant_code': 'EU_MERCHANT',
                'service_code': '401'
            },
            'campost': {
                'api_url': 'https://api.campost.cm/mobile',
                'merchant_code': 'CP_MERCHANT', 
                'service_code': '501'
            }
        }

        return configs.get(self.mobile_money_operator, {})

