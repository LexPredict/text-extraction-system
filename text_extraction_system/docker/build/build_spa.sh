#!/bin/bash

cd ../../text_extraction_system_ui
npm install
npm run build

echo "Current folder:"
pwd
ls -l

echo "Parent folder:"
ls -l ../

echo "Build folder:"
ls -l build

echo "Parent folder/TE:"
ls -l ../text_extraction_system

cp build/index.html ../text_extraction_system/templates
cd ../text_extraction_system/templates
sed -i 's/src=".\/bundle.js"/src="static\/bundle.js"/g' index.html