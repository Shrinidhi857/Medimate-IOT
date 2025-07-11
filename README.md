# 💊 IoT-Based Smart Tablet Dispenser

## 🧠 Overview
The **IoT-Based Smart Tablet Dispenser** is an innovative healthcare solution using **Raspberry Pi Zero 2 W**, **servo motors**, and **Firebase** to automate medication dispensing. It ensures timely intake, inventory tracking, and real-time alerts via a mobile app.

---
## Images
- ![alt text](medimate_hardware.png) 
- ![alt text](medimate_software.png)git
## 🎯 Objectives

### ✅ Primary
- Dispense tablets automatically using servo motors.
- Store & sync data with Firebase Realtime Database.
- Notify users via mobile app and buzzer/speaker.
- Work independently using a Li-Po battery.

### ✅ Secondary
- Improve medication adherence (especially for elderly).
- Allow remote monitoring for caregivers.
- Enable future enhancements (e.g., AI, sensors).

---

## ⚙️ Hardware Components

| Component             | Purpose                                |
|-----------------------|----------------------------------------|
| Raspberry Pi Zero 2 W | Main controller (Wi-Fi + GPIO)         |
| 2× Servo Motors       | Dispense tablets from compartments     |
| Speaker/Buzzer        | Audio alerts                           |
| Li-Po Battery         | Portable power supply                  |
| Bluetooth Module      | Optional local communication           |

---

## 🧰 Software & Tools

- **Python 3**
  - Libraries: `requests`, `time`, `json`, `threading`
- **Firebase Realtime Database**
- **Flutter App** (Android/iOS)
- **MQTT** (optional for real-time messaging)

---

## 🔄 System Workflow

1. **Schedule Setup**:
   - User or caregiver sets medication time and frequency via the mobile app.
2. **Firebase Sync**:
   - Data is pushed to Firebase in real-time.
3. **Raspberry Pi Actions**:
   - Fetches schedule from Firebase.
   - Compares current time.
   - Dispenses tablet using servo motor.
   - Triggers buzzer/speaker.
   - Updates database with success/failure and inventory count.
4. **Mobile App Alerts**:
   - User receives notification on dosage, missed doses, or low stock.

---

## 📲 Mobile App Features

- Set & manage schedules.
- View dosage history.
- Receive real-time alerts (e.g., "Tablet Dispensed", "Inventory Low").
- Update tablet stock remotely.

---

## 🛠️ Setup Instructions

### 1. Raspberry Pi Setup
```bash
sudo apt update
sudo apt install python3-pip
pip3 install requests firebase-admin
OT
