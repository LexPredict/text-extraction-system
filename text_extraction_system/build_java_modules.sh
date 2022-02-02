#!/bin/bash

mkdir -p java_modules

pushd text_extraction_system_java
mvn clean package dependency:copy-dependencies 

rm ../java_modules/*.jar
cp target/text_extraction_system_java-1.2.jar ../java_modules/
cp target/dependency/* ../java_modules/
popd