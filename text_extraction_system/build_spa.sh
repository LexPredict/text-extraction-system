#!/bin/bash

cd text_extraction_system_ui
echo "API_HOST=127.0.0.1:8000
API_PROTOCOL=https" >> .env
npm install
npm run build

cp build/index.html ../text_extraction_system/templates
cd ../text_extraction_system/templates
sed -i 's/src=".\/bundle.js"/src="static\/bundle.js"/g' index.html


