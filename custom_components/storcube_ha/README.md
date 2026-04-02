# Storcube

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![Version](https://img.shields.io/badge/version-1.2.3-blue.svg)
![Maintainer](https://img.shields.io/badge/maintainer-xez7082-green.svg)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)

Cette intégration personnalisée pour **Home Assistant** permet de surveiller et de piloter les batteries **Storcube** (et compatibles Baterway). Elle offre un suivi énergétique précis et permet d'automatiser votre stockage solaire via une connexion hybride Cloud/WebSocket.

## ✨ Fonctionnalités

- **Suivi en temps réel** : Niveau de batterie (%), puissance de charge/décharge (W), température et production PV.
- **Tableau de bord Énergie** : Entièrement compatible avec le dashboard Énergie natif de Home Assistant.
- **Contrôle à distance (Services)** : 
    - Ajustement de la puissance de sortie (Watts).
    - Définition du seuil de réserve de la batterie (%).
- **Maintenance** : Notification automatique lorsqu'une mise à jour logicielle (Firmware) est disponible.

## 🚀 Installation

### Option 1 : Via HACS (Recommandé)

1. Ouvrez **HACS** dans votre instance Home Assistant.
2. Allez dans **Intégrations**.
3. Cliquez sur les **trois points** en haut à droite et sélectionnez **Dépôts personnalisés**.
4. Ajoutez l'URL suivante : `https://github.com/xez7082/storcube_Ha`
5. Sélectionnez la catégorie **Intégration** et cliquez sur **Ajouter**.
6. Recherchez **"Storcube"**, cliquez dessus, puis sur **Télécharger**.
7. **Redémarrez Home Assistant.**

### Option 2 : Installation manuelle

1. Téléchargez le dossier `custom_components/storcube` de ce dépôt.
2. Copiez-le dans le dossier `config/custom_components/` de votre serveur.
3. **Redémarrez Home Assistant.**

## ⚙️ Configuration

1. Allez dans **Paramètres** > **Appareils et services**.
2. Cliquez sur **Ajouter une intégration** en bas à droite.
3. Recherchez **"Storcube"** dans la liste.
4. Remplissez le formulaire :
   - **Email / Identifiant** : Votre compte Storcube/Baterway.
   - **Mot de passe** : Votre mot de passe.
   - **Device ID** : L'identifiant unique situé sur l'étiquette de votre batterie.
   - **Broker MQTT** : L'adresse IP de votre broker (ex: `192.168.1.50`).

## 🛠 Services disponibles

L'intégration expose des services pour vos automatisations :

| Service | Description |
| :--- | :--- |
| `storcube.set_power` | Définit la puissance de sortie cible (W). |
| `storcube.set_threshold` | Définit le seuil minimum de décharge (%). |
| `storcube.check_firmware` | Vérifie manuellement si une mise à jour existe. |

## 📝 Versions

### v1.2.3
- Refonte de l'identité visuelle (Recherche simplifiée : **Storcube**).
- Optimisation des services de contrôle de puissance.
- Amélioration de la stabilité de la connexion WebSocket.
- Maintenance par **xez7082**.

## 🤝 Contribution & Support

Les contributions sont les bienvenues ! 
- Pour signaler un bug : [Ouvrir un ticket GitHub](https://github.com/xez7082/storcube_Ha/issues)
- Pour proposer une amélioration : Soumettez une **Pull Request**.

---

**Développé avec ❤️ par [xez7082](https://github.com/xez7082)**

*Note : Cette intégration est un projet indépendant et n'est pas officiellement affiliée à la marque Storcube.*
