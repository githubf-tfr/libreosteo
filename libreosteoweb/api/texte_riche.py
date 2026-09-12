# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Les 21 champs de texte riche, et la regle qui les protege (D6e, AR3).

**Le produit rognait les espaces de bord de ces 21 champs a chaque enregistrement**, sur
les deux surfaces et sans que rien ne le dise : `serializers.CharField.trim_whitespace` et
`forms.CharField.strip` valent tous deux `True` par defaut. Comme `savePatient()` reemettait
l'objet patient entier, **tout enregistrement du dossier rognait les neuf champs du patient**,
y compris ceux que le praticien n'avait pas touches.

L'arbitrage AR3 du 2026-09-12, rendu par l'utilisateur, l'arrete : aucune donnee medicale
n'est modifiee a l'enregistrement. C'est le **seul changement de comportement produit** du
lot D6e, et il va dans le sens de la conservation — un espace de tete conserve dans du HTML
n'a aucun effet au rendu.

La liste ci-dessous est **close** : `test_texte_riche.py` compte ses couples et verifie que
chacun nomme un `TextField` reel. Elle ne peut donc ni se trouer ni deriver en silence.
"""

from __future__ import annotations

from typing import Any, Iterator

from django import forms
from django.db import models as db_models
from rest_framework import serializers

from libreosteoweb import models

# Releve le 2026-09-12 sur `libreosteoweb/models.py`. Vingt et un couples exactement.
# `Examination.reason` n'en est pas : c'est un champ de texte simple (`editable-text`),
# pas un champ de texte riche. `Examination.status_reason` non plus.
CHAMPS_DE_TEXTE_RICHE: dict[str, tuple[str, ...]] = {
    "Patient": (
        "job",
        "hobbies",
        "important_info",
        "current_treatment",
        "surgical_history",
        "medical_history",
        "family_history",
        "trauma_history",
        "medical_reports",
    ),
    "Examination": (
        "reason_description",
        "orl",
        "visceral",
        "pulmo",
        "uro_gyneco",
        "periphery",
        "general_state",
        "medical_examination",
        "diagnosis",
        "treatments",
        "conclusion",
    ),
    "Document": ("notes",),
}

# Nombre de lignes lues d'un coup par `valeurs_de_texte_riche` (cf. sa docstring).
LOT_DE_LECTURE = 100

MODELES: dict[str, type[db_models.Model]] = {
    "Patient": models.Patient,
    "Examination": models.Examination,
    "Document": models.Document,
}


class ChampTexteRiche(forms.CharField):
    """Un champ de formulaire qui **ne rogne jamais** la valeur postee.

    `strip` est force ici et non passe par l'appelant : un appelant qui l'oublierait
    remettrait le rognage en place sans qu'aucun test ne le voie, sur un champ et un seul.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["strip"] = False
        super().__init__(*args, **kwargs)


def classes_de_champs(modele: type[db_models.Model]) -> dict[str, type[forms.Field]]:
    """Les `field_classes` a deposer dans le `Meta` d'un `ModelForm` de ce modele.

    Rend un dictionnaire vide pour un modele qui ne porte aucun champ de texte riche :
    l'appelant ne teste pas, il depose.
    """
    return {
        nom: ChampTexteRiche for nom in CHAMPS_DE_TEXTE_RICHE.get(modele.__name__, ())
    }


class SansRognageMixin(serializers.ModelSerializer):
    """Mixin de serialiseur DRF : les champs de texte riche ne sont plus rognes.

    Pose sur `get_fields()` et non dans `__init__` : `fields` est une propriete calculee
    paresseusement par DRF, et la modifier depuis `__init__` la forcerait a se construire
    avant que le serialiseur ne soit completement initialise.

    Herite de `serializers.ModelSerializer` pour que `self.Meta` et `super().get_fields()`
    soient tous deux definis ; les classes concretes declarent donc `(SansRognageMixin)`
    seul, l'ordre de resolution etant le meme qu'avec la base explicite.

    **Ce mixin reste en place apres D6e**, alors meme que les ecrans migres n'ecrivent plus
    par DRF (E15) : un reglage conservateur inerte ne coute rien, le retirer rouvrirait la
    question.
    """

    def get_fields(self) -> dict[str, serializers.Field]:
        champs = super().get_fields()
        for nom in CHAMPS_DE_TEXTE_RICHE.get(self.Meta.model.__name__, ()):
            champ = champs.get(nom)
            if isinstance(champ, serializers.CharField):
                champ.trim_whitespace = False
        return champs


def valeurs_de_texte_riche() -> Iterator[tuple[str, int, str, str]]:
    """Tout le corpus de texte riche non vide, sous forme (modele, id, champ, valeur).

    Consomme par la page de diagnostic (D6e, C7) et par elle seule. **Aucune ecriture** :
    cet iterateur lit, compte et rend ; il ne modifie rien, jamais.

    Une valeur vide (`""`) ou nulle (`None`, defaut de `Document.notes`) ne rend rien.
    L'ordre des quadruplets n'est pas garanti : il suit celui des modeles dans la table
    close, puis celui du gestionnaire par defaut.

    **Lu par lots, et c'est structurel** : un `.values(...)` nu remplit le cache de
    resultats du queryset avant le premier `yield`, c'est-a-dire tout l'HTML des
    consultations d'un cabinet charge en memoire du processus qui sert une page web.
    `.iterator()` ne remplit jamais ce cache. Le lot est fixe a 100 et non laisse au
    defaut de Django (2000) parce que la taille qui compte ici n'est pas le nombre de
    lignes mais leur poids : 2000 valeurs de texte riche, ce sont deja plusieurs dizaines
    de mega-octets.
    """
    for nom_modele, champs in CHAMPS_DE_TEXTE_RICHE.items():
        modele = MODELES[nom_modele]
        # `_default_manager` et non `objects` : c'est l'acces documente par Django au
        # gestionnaire d'un modele connu seulement par sa classe, et le seul que
        # `type[Model]` expose. `objects` n'est declare que sur les sous-classes.
        lignes = modele._default_manager.all().values("id", *champs)
        for ligne in lignes.iterator(chunk_size=LOT_DE_LECTURE):
            for champ in champs:
                valeur = ligne[champ]
                if valeur:
                    yield (nom_modele, ligne["id"], champ, valeur)
