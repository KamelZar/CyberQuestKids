# 🛡️ CyberQuest Kids - Interactive Cybersecurity Workshop

## 📋 About

This educational project was created for pedagogical purposes to introduce children to cybersecurity in a fun and interactive way. It's a 3D workshop that presents different aspects of cybersecurity through engaging and entertaining activities.

## 🎯 Objectives

- Raise awareness among young people about cybersecurity issues
- Learn good online security practices
- Discover different types of digital threats
- Develop critical thinking skills regarding online content

## 🎮 Features

- **Interactive 3D Interface**: Immersive navigation through an activity carousel
- **Varied Activities**: Privacy, passwords, phishing, deepfakes, and more
- **Progress System**: Unlock "Fantasy Quest" after completing all activities
- **Educational Content**: Simple explanations adapted for children
- **Gamified Experience**: Learning through play and interaction

## 🚀 Usage

### 🌐 Online Access (Recommended)

The workshop is accessible online via GitHub Pages:

**👉 [https://kamelzar.github.io/CyberQuestKids/html/workshop.html](https://kamelzar.github.io/CyberQuestKids/html/workshop.html)**

No installation required! Simply click the link and start exploring cybersecurity concepts.

### 💻 Local Development

For developers who want to run the project locally:

⚠️ **Important**: This project requires an HTTP server to work correctly (YouTube embedded videos don't work with `file:///` protocol).

**Option 1: Python HTTP Server**
```bash
cd html
python3 -m http.server 8000
```
Then open: `http://localhost:8000/workshop.html`

**Option 2: VS Code Live Server**
- Install the "Live Server" extension
- Right-click on `workshop.html` → "Open with Live Server"

**Option 3: Node.js HTTP Server**
```bash
npx http-server html -p 8000
```

### 🎮 How to Use

1. Navigate through the different activities
2. Complete all activities to unlock the final quest
3. Explore and learn!

## 📚 Project Structure

```
DevoxKids/
├── html/
│   ├── workshop.html    # Main workshop page
│   ├── page.html        # "Suspicious website" activity
│   ├── images/          # Visual resources
│   └── ...
└── README.md
```

## 🎓 Educational Context

This project is part of the Devoxx4Kids initiatives, aimed at making technology accessible and understandable for children. The playful approach allows addressing serious topics like cybersecurity in an age-appropriate manner for young audiences.

## 🎨 Assets Attribution

### 🎵 Music
All background music files are sourced from [Pixabay](https://pixabay.com/) - royalty-free music under Pixabay License. No copyright restrictions apply for educational use.

### 🖼️ Images
Background images and visual assets are generated using **Google Studio AI** (formerly Google Bard). These AI-generated images are created specifically for this educational project.

---

**Author:** Kamel Zaraoui  
**Location:** Belgium  
**Date:** September 2024  
**Context:** Educational and pedagogical project