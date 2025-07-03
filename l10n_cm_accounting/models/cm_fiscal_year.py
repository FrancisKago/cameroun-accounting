from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CmFiscalYear(models.Model):
    _name = 'cm.fiscal.year'
    _description = 'Exercice Fiscal Cameroun'
    _order = 'date_start desc'

    name = fields.Char(required=True, help="Nom de l'exercice (ex: 2025)")
    date_start = fields.Date(string="Date de d\u00e9but", required=True)
    date_end = fields.Date(string="Date de fin", required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    state = fields.Selection([
        ('open', 'Ouvert'),
        ('closed', 'Cl\u00f4tur\u00e9'),
    ], string="Statut", default='open', required=True)

    _sql_constraints = [
        ('unique_fiscal_year_per_company',
         'unique(company_id, date_start, date_end)',
         'Un exercice fiscal existe d\u00e9j\u00e0 pour cette p\u00e9riode et cette soci\u00e9t\u00e9.')
    ]

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start > record.date_end:
                raise ValidationError(_("La date de d\u00e9but ne peut pas \u00eatre apr\u00e8s la date de fin."))

    def action_close_fiscal_year(self):
        for record in self:
            if record.state == 'closed':
                raise ValidationError(_("L'exercice est d\u00e9j\u00e0 cl\u00f4tur\u00e9."))
            record.state = 'closed'

