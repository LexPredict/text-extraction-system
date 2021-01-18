#!/bin/bash

mkdir -p java_modules

pushd text_extraction_system_java
mvn clean package
cp target/text_extraction_system_java-1.0-jar-with-dependencies.jar ../java_modules/
popd