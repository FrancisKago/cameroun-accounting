/* global odoo */
odoo.define('l10n_cm_accounting.pos_mobile_money', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosPaymentScreenCameroon = PaymentScreen =>
        class extends PaymentScreen {
            /**
             * Extension du POS pour supporter Mobile Money camerounais
             */
            async validateOrder(isForceValidate) {
                // Vérifier les paiements Mobile Money
                const mobileMoneyPayments = this.currentOrder.get_paymentlines().filter(
                    line => line.payment_method.journal.mobile_money_operator
                );

                for (const payment of mobileMoneyPayments) {
                    if (!this.validateMobileMoneyPayment(payment)) {
                        return;
                    }
                }

                return super.validateOrder(isForceValidate);
            }

            validateMobileMoneyPayment(payment) {
                const journal = payment.payment_method.journal;
                const amount = payment.get_amount();

                // Vérifications spécifiques Mobile Money Cameroun
                if (amount <= 0) {
                    this.showPopup('ErrorPopup', {
                        title: 'Erreur Mobile Money',
                        body: 'Le montant doit être positif'
                    });
                    return false;
                }

                // Limites par opérateur
                const limits = {
                    'orange': 500000,  // 500k FCFA max par transaction
                    'mtn': 500000,
                    'express_union': 200000,
                    'campost': 100000
                };

                const limit = limits[journal.mobile_money_operator] || 500000;
                if (amount > limit) {
                    this.showPopup('ErrorPopup', {
                        title: 'Limite dépassée',
                        body: `Montant maximum autorisé: ${limit} FCFA`
                    });
                    return false;
                }

                return true;
            }

            /**
             * Ajouter des informations Mobile Money à la facture
             */
            async _postPushOrderResolve(order, server_ids) {
                const result = await super._postPushOrderResolve(order, server_ids);

                // Logger les transactions Mobile Money pour audit
                const mobileMoneyLines = order.get_paymentlines().filter(
                    line => line.payment_method.journal.mobile_money_operator
                );

                for (const line of mobileMoneyLines) {
                    console.log('Transaction Mobile Money:', {
                        operator: line.payment_method.journal.mobile_money_operator,
                        amount: line.get_amount(),
                        order_id: server_ids[0]
                    });
                }

                return result;
            }
        };

    Registries.Component.extend(PaymentScreen, PosPaymentScreenCameroon);

    return PosPaymentScreenCameroon;
});
