# TMG Material Browser

A Blender add-on for quickly browsing materials from `.blend` files, previewing them directly in the Tools panel, and appending or linking them to selected objects.

---

## ✅ Requirements

- [Blender 2.80 – 4.4.3](https://www.blender.org/download/)

---

## 📦 Installation

1. Save your `.blend` files containing materials into a folder.
2. In Blender, install the `tmg-material-browser.zip` add-on via **Edit > Preferences > Add-ons > Install**.
3. Once enabled, open the **Tools panel** (press `N` key).
4. Navigate to **TMG → Material Browser**.

---

## 🧪 How to Use

1. Click the 📁 **folder icon** in the Material Browser to select the directory containing your `.blend` files.
2. The add-on will auto-generate a `_Data` folder with:
   - A `.json` file listing all materials.
   - An optional `Previews` folder for `.png` preview images (see below).
3. **Preview images** must:
   - Be exactly **128x128 pixels**.
   - Be named **exactly** like the material they represent.
   - Be in `.png` format for best compatibility.
4. Click **Refresh** to update material data when materials are added/removed from `.blend` files.
5. Select one or more objects in the scene, then click a material in the list to append/link it to **slot 0** of the selected objects.

---

## 💡 Recommendations

- Stick to **128px previews** to keep performance fast and memory usage low.
- Supported preview formats: `.png` (tested), `.jpg` (partial support).
- Limit to **200 materials total** for optimal performance (can be increased based on system specs).
- For best results:
  - Store around **25 materials per blend file**.
  - Group them into **multiple .blend files** (e.g., 8 files × 25 materials = 200 total).
  - This setup provides fast loading, organized structure, and smoother material management.

---

## 🖼️ UI Screenshots

| Material List | Folder Selection | Full Panel View |
|---|---|---|
| ![Screenshot 1](https://github.com/user-attachments/assets/031df82e-36ae-4e93-aa87-40e4473b1a55) | ![Screenshot 2](https://github.com/user-attachments/assets/05ef9cf6-305e-4947-9b00-ded309f7b5be) | ![Screenshot 3](https://github.com/user-attachments/assets/43523d3e-088e-4137-94ea-9d3c1422aa30) |

---
