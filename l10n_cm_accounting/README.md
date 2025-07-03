# Module de Comptabilité Camerounaise pour Odoo 17

## Description

Module de localisation comptable pour le Cameroun, conforme aux normes SYSCOHADA et aux réglementations fiscales camerounaises.

## Fonctionnalités

### Plan Comptable SYSCOHADA
- Plan comptable complet conforme SYSCOHADA
- Structure hiérarchique par classes (1 à 8)
- Comptes spécifiques Mobile Money (573100, 573200)

### Taxes Camerounaises
- TVA 19,25% (taux standard)
- TVA 5,5% (taux réduit)
- Retenues à la source (5,5% et 11%)
- Taxe d'apprentissage (1%)
- Centimes communaux (10%)

### Déclarations Fiscales
- DSF (Déclaration Statistique et Fiscale)
- DIPE (Déclaration d'Impôt Provisionnel des Entreprises)
- IS (Impôt sur les Sociétés)
- Déclarations TVA mensuelles

### Gestion des Partenaires
- Validation des numéros de contribuable
- Régimes fiscaux camerounais
- Secteurs d'activité locaux
- Intégration Mobile Money

### Utilitaires
- Importation d'écritures via Excel
- Rappels fiscaux automatiques
- Transferts de fonds intégrés
- Gestion budgétaire
- Gestion manuelle des exercices fiscaux

## Installation

1. Décompresser l'archive dans le dossier `addons` d'Odoo
2. Redémarrer le serveur Odoo
3. Installer le module via Apps → Rechercher "Cameroon"

## Prérequis

- Odoo 17.0
- Python packages: pandas, xlrd, xlsxwriter

## Support

Pour toute question ou support, contactez l'équipe de développement.

## Licence

LGPL-3
