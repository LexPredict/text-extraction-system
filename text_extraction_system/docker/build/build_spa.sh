#!/bin/bash

cd ../../text_extraction_system_ui
npm install
npm run build

echo "Current folder:"
ls -l
pwd

cp build/index.html ../text_extraction_system/templates
cd ../text_extraction_system/templates
sed -i 's/src=".\/bundle.js"/src="static\/bundle.js"/g' index.html