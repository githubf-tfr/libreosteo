/**
    This file is part of LibreOsteo.

    LibreOsteo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    LibreOsteo is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
*/

/* Le comportement du composant de texte riche (D6e, C6).
 *
 * **Trois voies de saisie, trois ecoutes distinctes** — et c'est delibere : la frappe, le
 * collage et la commande de barre d'outils sont prouves separement, comme le lot D8 a
 * prouve le clic et la tabulation separement apres avoir decouvert que « le premier
 * inventaire d'un defaut n'epuise pas ses declencheurs ». Une ecoute unique sur `input`
 * couvrirait les trois en pratique, mais la neutraliser ne rendrait qu'un seul rouge, et
 * la preuve ne dirait plus laquelle des trois est cassee.
 *
 * `document.execCommand` est deprecie et implemente partout ; aucune suppression n'est
 * annoncee. C'est **la seule implementation qui produise le meme balisage que `hallo`**,
 * donc la seule qui ne fasse pas cohabiter deux dialectes HTML dans le meme champ. S'il
 * disparaissait, la barre d'outils cesserait de fonctionner **de facon visible**, et le
 * contenu deja saisi resterait intact : la preservation a l'octet ne le touche pas.
 *
 * Ce fichier est charge par `{% block js_page %}`, donc **apres** la balise
 * `<script defer>` d'Alpine mais **sans** `defer` lui-meme : il s'execute pendant
 * l'analyse du document, avant tout script differe. L'ecouteur `alpine:init` est donc en
 * place quand Alpine demarre.
 */
document.addEventListener('alpine:init', () => {
  Alpine.data('texteRiche', () => ({
    /* Le champ a-t-il le focus ? Pilote la seule visibilite de la barre d'outils, jamais
     * une ecriture : `hallo` n'affiche lui aussi qu'une barre a la fois, et neuf barres
     * empilees sur le dossier patient seraient un ecart d'ecran. */
    actif: false,

    /* Recopie l'HTML rendu vers l'entree cachee — la seule qui soit soumise.
     * Appelee **uniquement** depuis les trois voies ci-dessous : tant qu'aucune n'a
     * tire, l'entree cachee garde, octet pour octet, la valeur rendue par le serveur. */
    commettre() {
      this.$refs.cachee.value = this.$refs.zone.innerHTML;
    },

    commettreDepuisLaFrappe() {
      this.commettre();
    },

    /* Le collage est ecoute pour lui-meme. `$nextTick` : l'evenement `paste` se declenche
     * **avant** que le contenu ne soit insere dans le DOM ; lire `innerHTML` dans le
     * gestionnaire rendrait la valeur d'avant le collage. */
    commettreDepuisLeCollage() {
      this.$nextTick(() => this.commettre());
    },

    /* Le focus explicite avant `execCommand` n'est pas decoratif : la commande s'applique
     * a la selection du document. `@mousedown.prevent` sur le bouton empeche deja le focus
     * de quitter la zone ; `focus()` le restaure si le navigateur l'a quand meme relache
     * — par exemple quand la commande est declenchee au clavier et non a la souris. */
    commande(nom, valeur = null) {
      this.$refs.zone.focus();
      document.execCommand(nom, false, valeur);
      this.commettre();
    },
  }));
});
