
- Catégorie : `integration`

---

### 3. Installer l’intégration

- Rechercher **Storcube Battery Monitor**
- Télécharger
- Redémarrer Home Assistant

---

## ⚙️ Configuration

Dans Home Assistant :

Configuration → Appareils et services → Ajouter intégration

Rechercher : **Storcube Battery Monitor**

### Paramètres :

#### 🔌 Cloud (obligatoire)
- Login
- Password
- Device ID
- App Code (par défaut : Storcube)

#### 📡 MQTT (optionnel)
- Broker (ex: 192.168.1.xxx)
- Port (1883)
- Username (optionnel)
- Password (optionnel)

👉 Si MQTT non utilisé, laisser vide

---

## 🛠 Dépannage

### ❌ Pas de mise à jour

- Vérifier connexion Internet
- Vérifier identifiants Cloud
- Vérifier Device ID

### ❌ Erreur connexion

- Vérifier serveur Cloud
- Vérifier logs Home Assistant

---

## 📊 Support

- Documentation : https://github.com/xez7082/storcube_xez
- Issues : https://github.com/xez7082/storcube/issues

---

## 📄 Licence

MIT License

---

## 🤖 CI / Status

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

[![GitHub Release](https://img.shields.io/github/v/release/xez7082/storcube_xez)](https://github.com/xez7082/storcube_xez/releases)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/xez7082/storcube_xez/graphs/commit-activity)

[![GitHub stars](https://img.shields.io/github/stars/xez7082/storcube_xez?style=social)](https://github.com/xez7082/storcube_xez/stargazers)

[![Issues](https://img.shields.io/github/issues/xez7082/storcube_xez)](https://github.com/xez7082/storcube_xez/issues)
