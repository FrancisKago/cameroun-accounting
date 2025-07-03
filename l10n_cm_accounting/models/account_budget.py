# -*- coding: utf-8 -*-

"""Budget models for Cameroon localization."""

from odoo import models, fields, api, _

from odoo.exceptions import UserError


class AccountBudget(models.Model):
    _name = 'account.budget'
    """Budget master record."""
    _description = 'Budget comptable camerounais'
    _order = 'fiscal_year desc, name'

    name = fields.Char(string='Nom du budget', required=True)
    fiscal_year = fields.Integer(string='Exercice fiscal', required=True, default=lambda self: fields.Date.today().year)
    date_from = fields.Date(string='Date de début', required=True)
    date_to = fields.Date(string='Date de fin', required=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('validated', 'Validé'),
        ('done', 'Terminé')
    ], string='État', default='draft')

    budget_line_ids = fields.One2many('account.budget.line', 'budget_id', string='Lignes budgétaires')

    total_planned = fields.Monetary(string='Total planifié', compute='_compute_totals', store=True, currency_field='currency_id')
    total_realized = fields.Monetary(string='Total réalisé', compute='_compute_totals', store=True, currency_field='currency_id')
    total_variance = fields.Monetary(string='Écart total', compute='_compute_totals', store=True, currency_field='currency_id')

    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    @api.depends('budget_line_ids.planned_amount', 'budget_line_ids.realized_amount')
    def _compute_totals(self):
        for budget in self:
            budget.total_planned = sum(budget.budget_line_ids.mapped('planned_amount'))
            budget.total_realized = sum(budget.budget_line_ids.mapped('realized_amount'))
            budget.total_variance = budget.total_realized - budget.total_planned

    def action_confirm(self):
        self.state = 'confirmed'

    def action_validate(self):
        self.state = 'validated'

    def action_done(self):
        self.state = 'done'


class AccountBudgetLine(models.Model):
    """Individual budget line."""
    _name = 'account.budget.line'
    _description = 'Ligne budgétaire'

    budget_id = fields.Many2one('account.budget', string='Budget', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Compte', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Compte analytique')

    planned_amount = fields.Monetary(string='Montant planifié', currency_field='currency_id')
    realized_amount = fields.Monetary(string='Montant réalisé', compute='_compute_realized_amount', store=True, currency_field='currency_id')
    variance_amount = fields.Monetary(string='Écart', compute='_compute_variance', store=True, currency_field='currency_id')
    variance_percent = fields.Float(string='Écart (%)', compute='_compute_variance', store=True)

    currency_id = fields.Many2one('res.currency', related='budget_id.currency_id')

    @api.depends('budget_id.date_from', 'budget_id.date_to', 'account_id', 'analytic_account_id')
    def _compute_realized_amount(self):
        for line in self:
            if line.account_id and line.budget_id.date_from and line.budget_id.date_to:
                domain = [
                    ('account_id', '=', line.account_id.id),
                    ('date', '>=', line.budget_id.date_from),
                    ('date', '<=', line.budget_id.date_to),
                    ('move_id.state', '=', 'posted')
                ]

                if line.analytic_account_id:
                    domain.append(('analytic_account_id', '=', line.analytic_account_id.id))

                moves = self.env['account.move.line'].search(domain)
                line.realized_amount = sum(moves.mapped('balance'))
            else:
                line.realized_amount = 0

    @api.depends('planned_amount', 'realized_amount')
    def _compute_variance(self):
        for line in self:
            line.variance_amount = line.realized_amount - line.planned_amount
            if line.planned_amount:
                line.variance_percent = (line.variance_amount / line.planned_amount) * 100
            else:
                line.variance_percent = 0

