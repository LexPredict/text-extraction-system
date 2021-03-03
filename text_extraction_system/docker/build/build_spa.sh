#!/bin/bash

pushd .
cd ../../text_extraction_system_ui
sed -i "s/routerSubdir = ''/routerSubdir = 'TEXT_EXTRACTION_SPA_SUBDIRECTORY'/g" routing.ts
npm install
npm run build

cp build/index.html ../text_extraction_system/templates
cp build/bundle.js ../text_extraction_system/templates

cd ../text_extraction_system/templates
sed -i 's/src=".\/bundle.js"/src="static\/bundle.js"/g' index.html

popd