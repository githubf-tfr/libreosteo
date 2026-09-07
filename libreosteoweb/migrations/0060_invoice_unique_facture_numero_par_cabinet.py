# Migration ecrite a la main : l'`AddConstraint` que `makemigrations` produirait
# seul poserait la contrainte sur un parc qui peut deja porter des doublons, et
# la montee echouerait au demarrage. La reprise passe donc AVANT, dans la meme
# migration : sur PostgreSQL, une migration est transactionnelle, donc un echec
# de la contrainte annule aussi la renumerotation — il n'existe aucun etat
# intermediaire.
#
# La reprise renumerote, elle ne refuse pas (arbitrage A1 de la spec de D7). Un
# numero duplique est deja une anomalie et la seule correction possible est d'en
# liberer un ; refuser transformerait un historique en panne de facturation au
# demarrage. C'est l'inverse du choix de `0057`, et pour une raison qui tient a
# la donnee : un doublon de dossier patient est une donnee de sante dont la
# fusion est un acte medical, un doublon de numero de facture est une erreur de
# numerotation dont la reparation est mecanique.
#
# Retour arriere : `migrate libreosteoweb 0059` retire la contrainte et ne rend
# NI les anciens numeros NI la sequence d'avant. Meme asymetrie assumee que
# `0058`, qui rend `double precision` sans rendre les decimales perdues.
#
# Cette migration n'a AUCUN chemin d'echec sur les donnees, contrairement a 0057
# et a la garde de 0058 : le numero neuf attribue par la reprise domine toujours
# tous les numeros du cabinet, donc il ne peut entrer en collision avec aucun
# (demonstration dans `api/invoicing/reprise.py`, docstring de `planifier`). Il
# n'y a donc rien a convertir en CommandError ici, et une garde qui pretendrait
# le contraire serait du code mort.

from django.db import migrations, models

from libreosteoweb.api.invoicing import reprise


def reprendre_les_doublons(apps, schema_editor):
    reprise.appliquer(
        apps.get_model("libreosteoweb", "Invoice"),
        apps.get_model("libreosteoweb", "OfficeSettings"),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("libreosteoweb", "0059_alter_invoice_options"),
    ]

    operations = [
        migrations.RunPython(reprendre_les_doublons, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.UniqueConstraint(
                fields=("officesettings_id", "number"),
                name="unique_facture_numero_par_cabinet",
            ),
        ),
    ]
