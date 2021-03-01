#!/bin/bash

cd ../text_extraction_system_ui
npm run build

cp build/index.html ../text_extraction_system/text_extraction_system/templates
cd ../text_extraction_system/text_extraction_system/templates
sed -i 's/src=".\/bundle.js"/src="static\/bundle.js"/g' index.html