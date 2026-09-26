# Migration de donnees (F18) : purge unique de `django_session`, decidee au cadrage du
# 2026-09-26 en meme temps que l'exclusion des jetons de session de la sauvegarde et de la
# restauration (`backup_db.JETONS_DE_SESSION`, `sauvegarde.restaurer`). Cette exclusion ne
# protege que les archives a venir ; des archives deja telechargees peuvent encore porter
# d'anciennes sessions valides. Vider la table les rend toutes inoffensives d'un coup.
#
# Consequence assumee : chaque praticien actuellement connecte est deconnecte, et devra se
# reconnecter une fois a sa prochaine requete qui suit cette mise a jour.
#
# Retour arriere : aucune session supprimee n'est restituee (`RunPython.noop`), meme
# asymetrie que `0058` et `0060` -- une donnee purgee ne se reconstruit pas.

from django.db import migrations


def purger_les_sessions(apps, schema_editor):
    apps.get_model("sessions", "Session").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("libreosteoweb", "0060_invoice_unique_facture_numero_par_cabinet"),
        ("sessions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(purger_les_sessions, migrations.RunPython.noop),
    ]
