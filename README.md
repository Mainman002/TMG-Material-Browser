# tmg-material-browser
Parse materials in blend files, display material preview in tools panel, & append / link to selected objects.

## Requirements
[Blender 2.80 - 4.4.3]( https://www.blender.org/download/ )

## Instructions
* Save blend file with materials to a folder
* Install tmg-material-browser.zip file into blender
* Addon will be in the side Tools panel (N key to toggle)
* TMG -> Material Browser
* Inside the Material Browser panel click the folder icon to select the folder containing your blend files
* This generates a _data folder containing a json file of all materials * a previews folder can be setup containing png images
* If you add preview images make them 128px png named exactly like your material it references else it wont be detected
* The refresh button can be used to regenerate the json data if you add / remove materials in the blend file
* Select objects in the scene to append / link the selected material (Only swaps material slot 0 of selected objects)

## Recomenedations
* Keep previews around 128px to reduce backround processing
* .png & .jpg file formats are supported currently (.png have been tested)
* Loading a max of 200 materials is a good safe range but more can be used if your PC can handle it
* Using around 25 materisl per blend file is recomended for fast append / linking of materials
* I store 25 materials in a blend file & have 8 blend files in a folder (200 materials total when accessed) This is optimial for my use case

<img width="242" alt="Screenshot 2025-05-31 at 8 53 35 PM" src="https://github.com/user-attachments/assets/031df82e-36ae-4e93-aa87-40e4473b1a55" />
<img width="1800" alt="Screenshot 2025-05-31 at 8 53 27 PM" src="https://github.com/user-attachments/assets/05ef9cf6-305e-4947-9b00-ded309f7b5be" />
<img width="1912" alt="Screenshot 2025-05-31 at 9 08 11 PM" src="https://github.com/user-attachments/assets/43523d3e-088e-4137-94ea-9d3c1422aa30" />
