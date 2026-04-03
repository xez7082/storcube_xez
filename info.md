# Storcube Battery Monitor

Intégration Home Assistant pour les batteries Storcube avec support Cloud et MQTT.

---

## 📦 Installation via HACS

### 1. Prérequis
- HACS installé dans Home Assistant
- Un broker MQTT fonctionnel (si utilisé)
- Identifiants de votre compte Storcube
- Device ID de votre batterie

---

### 2. Ajout du dépôt HACS

Dans Home Assistant :

- Ouvrir **HACS**
- Aller dans **Intégrations**
- Cliquer sur **⋮ (menu)**
- Sélectionner **Dépôts personnalisés**
- Ajouter l’URL : https://github.com/xez7082/storcube_xez


- Catégorie : `integration`
- Valider

---

### 3. Installation

- Rechercher **Storcube Battery Monitor**
- Cliquer sur **Télécharger**
- Redémarrer Home Assistant

---

### 4. Configuration

Aller dans :

**Configuration → Appareils et services → Ajouter une intégration**

Rechercher : **Storcube Battery Monitor**

Renseigner :

- Broker MQTT (ex: 192.168.1.xxx) *(optionnel)*
- Port MQTT (par défaut 1883)
- Device ID (indiqué sur la batterie ou app)
- Identifiants Cloud Storcube
  - Login
  - Mot de passe

---

## 🔋 Capteurs disponibles

- Niveau de batterie (%)
- Puissance de sortie (W)
- Seuil de batterie (%)
- Température batterie
- État de connexion
- Firmware version

---

## 🛠 Support

- Documentation : https://github.com/xez7082/storcube
- Issues : https://github.com/xez7082/storcube/issues

![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)

Compatible Home Assistant 2024+
